import time

from app.services import publication_queue as pq
from tests.conftest import insert_place


def _insert_queue_row(conn, place_id, status="pending", attempts=0, max_attempts=3,
                       last_error=None, started_at=None, finished_at=None, created_at=None):
    conn.execute(
        """
        INSERT INTO publication_queue
            (place_id, status, attempts, max_attempts, last_error,
             created_at, started_at, finished_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (place_id, status, attempts, max_attempts, last_error,
         created_at or int(time.time()), started_at, finished_at),
    )
    conn.commit()


def _set_control(conn, active=0, interval_seconds=300, next_run_at=None):
    conn.execute(
        """
        UPDATE publication_queue_control
        SET active = ?, interval_seconds = ?, next_run_at = ?, updated_at = ?
        WHERE id = 1
        """,
        (active, interval_seconds, next_run_at, int(time.time())),
    )
    conn.commit()


# --- enqueue_pending_places -------------------------------------------------

def test_enqueue_adds_only_unpublished_unqueued_places(temp_db, conn):
    insert_place(conn, "a", publicado_en_wp=0)
    insert_place(conn, "b", publicado_en_wp=1)  # ya publicado: no elegible
    insert_place(conn, "c", publicado_en_wp=0)

    added = pq.enqueue_pending_places(limit=10)

    assert added == 2
    rows = conn.execute("SELECT place_id FROM publication_queue ORDER BY place_id").fetchall()
    assert [r["place_id"] for r in rows] == ["a", "c"]


def test_enqueue_does_not_duplicate_already_queued(temp_db, conn):
    insert_place(conn, "a", publicado_en_wp=0)
    _insert_queue_row(conn, "a", status="pending")

    added = pq.enqueue_pending_places(limit=10)

    assert added == 0
    rows = conn.execute("SELECT COUNT(*) AS n FROM publication_queue").fetchone()
    assert rows["n"] == 1


def test_enqueue_respects_limit(temp_db, conn):
    for i in range(5):
        insert_place(conn, f"p{i}", publicado_en_wp=0)

    added = pq.enqueue_pending_places(limit=2)

    assert added == 2


# --- start_queue / pause_queue / resume_queue -------------------------------

def test_start_queue_activates_and_sets_next_run_at(temp_db, conn):
    insert_place(conn, "a", publicado_en_wp=0)

    result = pq.start_queue(limit=10, interval_seconds=120)

    assert result["added"] == 1
    assert result["active"] is True
    assert result["interval_seconds"] == 120
    assert result["next_run_at"] is not None


def test_start_queue_preserves_next_run_at_if_already_active(temp_db, conn):
    _set_control(conn, active=1, next_run_at=999999)

    result = pq.start_queue(limit=10, interval_seconds=60)

    assert result["next_run_at"] == 999999


def test_pause_queue_deactivates(temp_db, conn):
    _set_control(conn, active=1)

    result = pq.pause_queue()

    assert result["active"] is False


def test_resume_queue_reactivates_only_with_pending(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")
    _set_control(conn, active=0)

    result = pq.resume_queue()

    assert result["active"] is True
    assert result["next_run_at"] is not None


def test_resume_queue_stays_inactive_without_pending(temp_db, conn):
    _set_control(conn, active=0)

    result = pq.resume_queue()

    assert result["active"] is False
    assert result["next_run_at"] is None


# --- retry_failed ------------------------------------------------------------

def test_retry_failed_resets_only_failed_rows(temp_db, conn):
    insert_place(conn, "a")
    insert_place(conn, "b")
    _insert_queue_row(conn, "a", status="failed", attempts=3, last_error="boom")
    _insert_queue_row(conn, "b", status="completed", attempts=1)

    result = pq.retry_failed()

    assert result["retried"] == 1
    a = conn.execute("SELECT * FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert a["status"] == "pending"
    assert a["attempts"] == 0
    assert a["last_error"] is None
    b = conn.execute("SELECT * FROM publication_queue WHERE place_id = 'b'").fetchone()
    assert b["status"] == "completed"  # sin tocar


def test_retry_failed_does_not_reactivate_when_nothing_changed(temp_db, conn):
    _set_control(conn, active=0)

    result = pq.retry_failed()

    assert result["retried"] == 0
    assert result["active"] is False


# --- get_queue_status ---------------------------------------------------------

def test_get_queue_status_counts_and_current(temp_db, conn):
    for pid, status in [("a", "pending"), ("b", "processing"), ("c", "completed"), ("d", "failed")]:
        insert_place(conn, pid)
        _insert_queue_row(conn, pid, status=status, attempts=1)

    status = pq.get_queue_status()

    assert status["pending"] == 1
    assert status["processing"] == 1
    assert status["completed"] == 1
    assert status["failed"] == 1
    assert status["total"] == 4
    assert status["current"]["place_id"] == "b"


def test_get_queue_status_recent_errors_limited_and_ordered(temp_db, conn):
    for i in range(7):
        pid = f"p{i}"
        insert_place(conn, pid)
        _insert_queue_row(
            conn, pid, status="failed", attempts=3,
            last_error=f"error {i}", finished_at=1000 + i,
        )

    status = pq.get_queue_status()

    assert len(status["recent_errors"]) == 5
    # el mas reciente (finished_at mas alto) primero
    assert status["recent_errors"][0]["place_id"] == "p6"


# --- _claim_next ---------------------------------------------------------------

def test_claim_next_returns_none_when_inactive(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")
    _set_control(conn, active=0)

    assert pq._claim_next() is None


def test_claim_next_respects_next_run_at_throttle(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")
    _set_control(conn, active=1, next_run_at=int(time.time()) + 3600)

    assert pq._claim_next() is None


def test_claim_next_claims_oldest_pending_and_marks_processing(temp_db, conn):
    insert_place(conn, "a")
    insert_place(conn, "b")
    _insert_queue_row(conn, "a", status="pending", created_at=1)
    _insert_queue_row(conn, "b", status="pending", created_at=2)
    _set_control(conn, active=1, interval_seconds=300)

    claimed = pq._claim_next()

    assert claimed == "a"
    row = conn.execute("SELECT * FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "processing"
    assert row["attempts"] == 1
    assert row["started_at"] is not None
    control = conn.execute("SELECT next_run_at, active FROM publication_queue_control").fetchone()
    assert control["active"] == 1
    assert control["next_run_at"] > int(time.time())


def test_claim_next_deactivates_when_nothing_claimable(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending", attempts=3, max_attempts=3)  # agotado
    _set_control(conn, active=1)

    claimed = pq._claim_next()

    assert claimed is None
    control = conn.execute("SELECT active, next_run_at FROM publication_queue_control").fetchone()
    assert control["active"] == 0
    assert control["next_run_at"] is None


# --- _finish ---------------------------------------------------------------------

def test_finish_success_marks_completed(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="processing", attempts=1)

    pq._finish("a")

    row = conn.execute("SELECT * FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "completed"
    assert row["last_error"] is None


def test_finish_error_with_attempts_left_goes_pending(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="processing", attempts=1, max_attempts=3)

    pq._finish("a", error="algo fallo")

    row = conn.execute("SELECT * FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "pending"
    assert row["last_error"] == "algo fallo"


def test_finish_error_without_attempts_left_goes_failed(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="processing", attempts=3, max_attempts=3)

    pq._finish("a", error="algo fallo")

    row = conn.execute("SELECT * FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "failed"


# --- _process_once (sin tocar OpenAI/WordPress/Google) --------------------------

def test_process_once_returns_none_when_queue_empty(temp_db, conn):
    _set_control(conn, active=1)

    assert pq._process_once() is None


def test_process_once_marks_completed_on_success(temp_db, conn, monkeypatch):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")
    _set_control(conn, active=1)
    monkeypatch.setattr(pq, "_run_pipeline", lambda place_id: None)

    result = pq._process_once()

    assert result == "a"
    row = conn.execute("SELECT status FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "completed"


def test_process_once_records_error_on_pipeline_failure(temp_db, conn, monkeypatch):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending", attempts=0, max_attempts=3)
    _set_control(conn, active=1)

    def _boom(place_id):
        raise RuntimeError("fallo simulado en el pipeline")

    monkeypatch.setattr(pq, "_run_pipeline", _boom)

    result = pq._process_once()

    assert result == "a"
    row = conn.execute("SELECT status, last_error FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "pending"  # le quedaban intentos
    assert "fallo simulado" in row["last_error"]
