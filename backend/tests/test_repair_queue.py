import time

from app.services import repair_queue as rq
from tests.conftest import add_fake_image, insert_place


def _insert_queue_row(conn, place_id, status="pending", attempts=0, max_attempts=3,
                       last_error=None, started_at=None, finished_at=None, created_at=None):
    conn.execute(
        """
        INSERT INTO repair_queue
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
        UPDATE repair_queue_control
        SET active = ?, interval_seconds = ?, next_run_at = ?, updated_at = ?
        WHERE id = 1
        """,
        (active, interval_seconds, next_run_at, int(time.time())),
    )
    conn.commit()


# --- enqueue_incomplete_places ------------------------------------------------

def test_enqueue_adds_only_incomplete_places(temp_db, conn, tmp_path):
    insert_place(conn, "a")  # sin imagen -> incompleta
    insert_place(conn, "b")
    add_fake_image(conn, tmp_path, "b")  # b queda completa

    added = rq.enqueue_incomplete_places(limit=10)

    assert added == 1
    rows = conn.execute("SELECT place_id FROM repair_queue").fetchall()
    assert [r["place_id"] for r in rows] == ["a"]


def test_enqueue_skips_already_pending_or_processing(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")

    added = rq.enqueue_incomplete_places(limit=10)

    assert added == 0
    rows = conn.execute("SELECT COUNT(*) AS n FROM repair_queue").fetchone()
    assert rows["n"] == 1


def test_enqueue_reactivates_completed_or_failed_rows(temp_db, conn):
    insert_place(conn, "a")  # sigue incompleta (sin imagen)
    _insert_queue_row(conn, "a", status="failed", attempts=3, last_error="boom")

    added = rq.enqueue_incomplete_places(limit=10)

    assert added == 1
    row = conn.execute("SELECT * FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert row["last_error"] is None


def test_enqueue_respects_limit(temp_db, conn):
    for i in range(5):
        insert_place(conn, f"p{i}")

    added = rq.enqueue_incomplete_places(limit=2)

    assert added == 2


# --- start_queue / pause_queue / resume_queue -------------------------------

def test_start_queue_activates_only_if_pending_after_enqueue(temp_db, conn):
    insert_place(conn, "a")

    result = rq.start_queue(limit=10, interval_seconds=90)

    assert result["added"] == 1
    assert result["active"] is True
    assert result["interval_seconds"] == 90


def test_start_queue_stays_inactive_without_incomplete_places(temp_db, conn):
    result = rq.start_queue(limit=10)

    assert result["added"] == 0
    assert result["active"] is False


def test_pause_queue_deactivates(temp_db, conn):
    _set_control(conn, active=1)

    result = rq.pause_queue()

    assert result["active"] is False


def test_resume_queue_reactivates_only_with_pending(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")
    _set_control(conn, active=0)

    result = rq.resume_queue()

    assert result["active"] is True


def test_resume_queue_stays_inactive_without_pending(temp_db, conn):
    _set_control(conn, active=0)

    result = rq.resume_queue()

    assert result["active"] is False
    assert result["next_run_at"] is None


# --- retry_failed ------------------------------------------------------------

def test_retry_failed_resets_only_failed_rows(temp_db, conn):
    insert_place(conn, "a")
    insert_place(conn, "b")
    _insert_queue_row(conn, "a", status="failed", attempts=3, last_error="boom")
    _insert_queue_row(conn, "b", status="completed", attempts=1)

    result = rq.retry_failed()

    assert result["retried"] == 1
    a = conn.execute("SELECT * FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert a["status"] == "pending"
    b = conn.execute("SELECT * FROM repair_queue WHERE place_id = 'b'").fetchone()
    assert b["status"] == "completed"


# --- get_queue_status ---------------------------------------------------------

def test_get_queue_status_counts_and_current(temp_db, conn):
    for pid, status in [("a", "pending"), ("b", "processing"), ("c", "completed"), ("d", "failed")]:
        insert_place(conn, pid)
        _insert_queue_row(conn, pid, status=status, attempts=1)

    status = rq.get_queue_status()

    assert status["pending"] == 1
    assert status["processing"] == 1
    assert status["completed"] == 1
    assert status["failed"] == 1
    assert status["current"]["place_id"] == "b"


def test_get_queue_status_ignores_blank_errors(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="failed", attempts=3, last_error="   ", finished_at=100)

    status = rq.get_queue_status()

    # last_error en blanco (solo espacios) no debe contar como error real
    assert status["recent_errors"] == []


# --- _claim_next ---------------------------------------------------------------

def test_claim_next_returns_none_when_inactive(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")
    _set_control(conn, active=0)

    assert rq._claim_next() is None


def test_claim_next_claims_oldest_pending_and_marks_processing(temp_db, conn):
    insert_place(conn, "a")
    insert_place(conn, "b")
    _insert_queue_row(conn, "a", status="pending", created_at=1)
    _insert_queue_row(conn, "b", status="pending", created_at=2)
    _set_control(conn, active=1, interval_seconds=300)

    claimed = rq._claim_next()

    assert claimed == "a"
    row = conn.execute("SELECT * FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "processing"
    assert row["attempts"] == 1


def test_claim_next_deactivates_when_nothing_claimable(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending", attempts=3, max_attempts=3)
    _set_control(conn, active=1)

    claimed = rq._claim_next()

    assert claimed is None
    control = conn.execute("SELECT active, next_run_at FROM repair_queue_control").fetchone()
    assert control["active"] == 0
    assert control["next_run_at"] is None


# --- _finish ---------------------------------------------------------------------

def test_finish_success_marks_completed(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="processing", attempts=1)

    rq._finish("a")

    row = conn.execute("SELECT status FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "completed"


def test_finish_error_with_attempts_left_goes_pending(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="processing", attempts=1, max_attempts=3)

    rq._finish("a", error="algo fallo")

    row = conn.execute("SELECT status FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "pending"


def test_finish_error_without_attempts_left_goes_failed(temp_db, conn):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="processing", attempts=3, max_attempts=3)

    rq._finish("a", error="algo fallo")

    row = conn.execute("SELECT status FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "failed"


# --- _process_once (sin tocar OpenAI/WordPress/Google) --------------------------

def test_process_once_returns_none_when_queue_empty(temp_db, conn):
    _set_control(conn, active=1)

    assert rq._process_once() is None


def test_process_once_marks_completed_on_success(temp_db, conn, monkeypatch):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending")
    _set_control(conn, active=1)
    monkeypatch.setattr(rq, "_repair_place", lambda place_id: None)

    result = rq._process_once()

    assert result == "a"
    row = conn.execute("SELECT status FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "completed"


def test_process_once_records_error_on_repair_failure(temp_db, conn, monkeypatch):
    insert_place(conn, "a")
    _insert_queue_row(conn, "a", status="pending", attempts=0, max_attempts=3)
    _set_control(conn, active=1)

    def _boom(place_id):
        raise RuntimeError("fallo simulado en la reparacion")

    monkeypatch.setattr(rq, "_repair_place", _boom)

    result = rq._process_once()

    assert result == "a"
    row = conn.execute("SELECT status, last_error FROM repair_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "pending"
    assert "fallo simulado" in row["last_error"]
