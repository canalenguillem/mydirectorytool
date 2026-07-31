import time

from app.services import seed_queue as sq


def _insert_queue_row(conn, seed_location_id, search_term="restaurantes", status="pending",
                       attempts=0, max_attempts=3, last_error=None, started_at=None,
                       finished_at=None, created_at=None):
    conn.execute(
        """
        INSERT INTO seed_queue
            (seed_location_id, search_term, status, attempts, max_attempts, last_error,
             created_at, started_at, finished_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (seed_location_id, search_term, status, attempts, max_attempts, last_error,
         created_at or int(time.time()), started_at, finished_at),
    )
    conn.commit()


def _set_control(conn, active=0, interval_seconds=300, next_run_at=None):
    conn.execute(
        """
        UPDATE seed_queue_control
        SET active = ?, interval_seconds = ?, next_run_at = ?, updated_at = ?
        WHERE id = 1
        """,
        (active, interval_seconds, next_run_at, int(time.time())),
    )
    conn.commit()


# --- enqueue_locations -------------------------------------------------------

def test_enqueue_adds_only_active_unqueued_locations(temp_db, conn, make_seed_location):
    a = make_seed_location("Palma", country_code="ES")
    make_seed_location("Ciudad Inactiva", country_code="ES", active=0)  # no elegible
    c = make_seed_location("Madrid", country_code="ES")

    added = sq.enqueue_locations("restaurantes", None, limit=10)

    assert added == 2
    rows = conn.execute("SELECT seed_location_id FROM seed_queue ORDER BY seed_location_id").fetchall()
    assert [r["seed_location_id"] for r in rows] == sorted([a, c])


def test_enqueue_does_not_duplicate_same_search_term(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, search_term="restaurantes", status="pending")

    added = sq.enqueue_locations("restaurantes", None, limit=10)

    assert added == 0
    total = conn.execute("SELECT COUNT(*) AS n FROM seed_queue").fetchone()
    assert total["n"] == 1


def test_enqueue_allows_same_location_with_different_search_term(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, search_term="restaurantes", status="completed")

    added = sq.enqueue_locations("peluquerias", None, limit=10)

    assert added == 1
    terms = {r["search_term"] for r in conn.execute("SELECT search_term FROM seed_queue").fetchall()}
    assert terms == {"restaurantes", "peluquerias"}


def test_enqueue_respects_country_code_filter(temp_db, conn, make_seed_location):
    make_seed_location("Palma", country_code="ES")
    make_seed_location("Houston", country_code="US")

    added = sq.enqueue_locations("restaurantes", "US", limit=10)

    assert added == 1
    row = conn.execute(
        """
        SELECT sl.country_code FROM seed_queue q
        JOIN seed_location sl ON sl.id = q.seed_location_id
        """
    ).fetchone()
    assert row["country_code"] == "US"


def test_enqueue_respects_limit(temp_db, conn, make_seed_location):
    for i in range(5):
        make_seed_location(f"Ciudad{i}", country_code="ES")

    added = sq.enqueue_locations("restaurantes", None, limit=2)

    assert added == 2


# --- start_queue / pause_queue / resume_queue -------------------------------

def test_start_queue_activates_and_sets_next_run_at(temp_db, conn, make_seed_location):
    make_seed_location("Palma", country_code="ES")

    result = sq.start_queue("restaurantes", None, limit=10, interval_seconds=120)

    assert result["added"] == 1
    assert result["active"] is True
    assert result["interval_seconds"] == 120
    assert result["next_run_at"] is not None
    assert result["search_term"] == "restaurantes"


def test_start_queue_preserves_next_run_at_if_already_active(temp_db, conn, make_seed_location):
    _set_control(conn, active=1, next_run_at=999999)

    result = sq.start_queue("restaurantes", None, limit=10, interval_seconds=60)

    assert result["next_run_at"] == 999999


def test_pause_queue_deactivates(temp_db, conn):
    _set_control(conn, active=1)

    result = sq.pause_queue()

    assert result["active"] is False


def test_resume_queue_reactivates_only_with_pending(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="pending")
    _set_control(conn, active=0)

    result = sq.resume_queue()

    assert result["active"] is True
    assert result["next_run_at"] is not None


def test_resume_queue_stays_inactive_without_pending(temp_db, conn):
    _set_control(conn, active=0)

    result = sq.resume_queue()

    assert result["active"] is False
    assert result["next_run_at"] is None


# --- retry_failed ------------------------------------------------------------

def test_retry_failed_resets_only_failed_rows(temp_db, conn, make_seed_location):
    a = make_seed_location("Palma", country_code="ES")
    b = make_seed_location("Madrid", country_code="ES")
    _insert_queue_row(conn, a, status="failed", attempts=3, last_error="boom")
    _insert_queue_row(conn, b, status="completed", attempts=1)

    result = sq.retry_failed()

    assert result["retried"] == 1
    row_a = conn.execute("SELECT * FROM seed_queue WHERE seed_location_id = ?", (a,)).fetchone()
    assert row_a["status"] == "pending"
    assert row_a["attempts"] == 0
    assert row_a["last_error"] is None
    row_b = conn.execute("SELECT * FROM seed_queue WHERE seed_location_id = ?", (b,)).fetchone()
    assert row_b["status"] == "completed"


def test_retry_failed_does_not_reactivate_when_nothing_changed(temp_db, conn):
    _set_control(conn, active=0)

    result = sq.retry_failed()

    assert result["retried"] == 0
    assert result["active"] is False


# --- get_queue_status ---------------------------------------------------------

def test_get_queue_status_counts_and_current(temp_db, conn, make_seed_location):
    ids = {}
    for name, status in [("a", "pending"), ("b", "processing"), ("c", "completed"), ("d", "failed")]:
        ids[name] = make_seed_location(name, country_code="ES")
        _insert_queue_row(conn, ids[name], status=status, attempts=1)

    status = sq.get_queue_status()

    assert status["pending"] == 1
    assert status["processing"] == 1
    assert status["completed"] == 1
    assert status["failed"] == 1
    assert status["total"] == 4
    assert status["current"]["seed_location_id"] == ids["b"]


def test_get_queue_status_recent_errors_limited_and_ordered(temp_db, conn, make_seed_location):
    for i in range(7):
        loc_id = make_seed_location(f"Ciudad{i}", country_code="ES")
        _insert_queue_row(
            conn, loc_id, status="failed", attempts=3,
            last_error=f"error {i}", finished_at=1000 + i,
        )

    status = sq.get_queue_status()

    assert len(status["recent_errors"]) == 5
    assert status["recent_errors"][0]["name"] == "Ciudad6"


# --- _claim_next ---------------------------------------------------------------

def test_claim_next_returns_none_when_inactive(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="pending")
    _set_control(conn, active=0)

    assert sq._claim_next() is None


def test_claim_next_respects_next_run_at_throttle(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="pending")
    _set_control(conn, active=1, next_run_at=int(time.time()) + 3600)

    assert sq._claim_next() is None


def test_claim_next_claims_oldest_pending_and_marks_processing(temp_db, conn, make_seed_location):
    a = make_seed_location("Palma", country_code="ES")
    b = make_seed_location("Madrid", country_code="ES")
    _insert_queue_row(conn, a, status="pending", created_at=1)
    _insert_queue_row(conn, b, status="pending", created_at=2)
    _set_control(conn, active=1, interval_seconds=300)

    claimed = sq._claim_next()

    assert claimed["seed_location_id"] == a
    assert claimed["search_term"] == "restaurantes"
    row = conn.execute("SELECT * FROM seed_queue WHERE seed_location_id = ?", (a,)).fetchone()
    assert row["status"] == "processing"
    assert row["attempts"] == 1
    assert row["started_at"] is not None
    control = conn.execute("SELECT next_run_at, active FROM seed_queue_control").fetchone()
    assert control["active"] == 1
    assert control["next_run_at"] > int(time.time())


def test_claim_next_deactivates_when_nothing_claimable(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="pending", attempts=3, max_attempts=3)
    _set_control(conn, active=1)

    claimed = sq._claim_next()

    assert claimed is None
    control = conn.execute("SELECT active, next_run_at FROM seed_queue_control").fetchone()
    assert control["active"] == 0
    assert control["next_run_at"] is None


# --- _finish ---------------------------------------------------------------------

def test_finish_success_marks_completed(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="processing", attempts=1)
    row = conn.execute("SELECT id FROM seed_queue WHERE seed_location_id = ?", (palma,)).fetchone()

    sq._finish(row["id"], found=42, saved=20)

    updated = conn.execute("SELECT * FROM seed_queue WHERE id = ?", (row["id"],)).fetchone()
    assert updated["status"] == "completed"
    assert updated["last_error"] is None
    assert updated["places_found"] == 42
    assert updated["places_saved"] == 20


def test_finish_error_with_attempts_left_goes_pending(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="processing", attempts=1, max_attempts=3)
    row = conn.execute("SELECT id FROM seed_queue WHERE seed_location_id = ?", (palma,)).fetchone()

    sq._finish(row["id"], error="algo fallo")

    updated = conn.execute("SELECT * FROM seed_queue WHERE id = ?", (row["id"],)).fetchone()
    assert updated["status"] == "pending"
    assert updated["last_error"] == "algo fallo"


def test_finish_error_without_attempts_left_goes_failed(temp_db, conn, make_seed_location):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="processing", attempts=3, max_attempts=3)
    row = conn.execute("SELECT id FROM seed_queue WHERE seed_location_id = ?", (palma,)).fetchone()

    sq._finish(row["id"], error="algo fallo")

    updated = conn.execute("SELECT * FROM seed_queue WHERE id = ?", (row["id"],)).fetchone()
    assert updated["status"] == "failed"


# --- _process_once (sin tocar Google real) ------------------------------------

def test_process_once_returns_none_when_queue_empty(temp_db, conn):
    _set_control(conn, active=1)

    assert sq._process_once() is None


def test_process_once_marks_completed_on_success(temp_db, conn, make_seed_location, monkeypatch):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="pending")
    _set_control(conn, active=1)
    monkeypatch.setattr(
        sq, "_run_pipeline",
        lambda seed_location_id, search_term: {"found": 30, "top": 20, "saved": 20},
    )

    result = sq._process_once()

    assert result["seed_location_id"] == palma
    row = conn.execute("SELECT status, places_found, places_saved FROM seed_queue WHERE seed_location_id = ?", (palma,)).fetchone()
    assert row["status"] == "completed"
    assert row["places_found"] == 30
    assert row["places_saved"] == 20


def test_process_once_records_error_on_pipeline_failure(temp_db, conn, make_seed_location, monkeypatch):
    palma = make_seed_location("Palma", country_code="ES")
    _insert_queue_row(conn, palma, status="pending", attempts=0, max_attempts=3)
    _set_control(conn, active=1)

    def _boom(seed_location_id, search_term):
        raise RuntimeError("fallo simulado contra la API de Google")

    monkeypatch.setattr(sq, "_run_pipeline", _boom)

    result = sq._process_once()

    assert result["seed_location_id"] == palma
    row = conn.execute("SELECT status, last_error FROM seed_queue WHERE seed_location_id = ?", (palma,)).fetchone()
    assert row["status"] == "pending"  # le quedaban intentos
    assert "fallo simulado" in row["last_error"]
