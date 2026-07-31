import time

import pytest
from fastapi import HTTPException

from app.api import roundups as roundups_api
from app.models import database
from app.services import publication_queue as pq
from app.services import roundup_queue as rq
from tests.conftest import insert_place


def _set_control(conn, active=0, interval_seconds=15, next_run_at=None):
    conn.execute(
        """
        UPDATE roundup_queue_control
        SET active = ?, interval_seconds = ?, next_run_at = ?, updated_at = ?
        WHERE id = 1
        """,
        (active, interval_seconds, next_run_at, int(time.time())),
    )
    conn.commit()


def _insert_job(conn, tema="cesta de prueba", status="pending", attempts=0, max_attempts=3,
                 post_id=None, basket_id=None, created_at=None):
    cur = conn.execute(
        """
        INSERT INTO roundup_queue (tema, post_id, basket_id, status, attempts, max_attempts, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (tema, post_id, basket_id, status, attempts, max_attempts, created_at or int(time.time())),
    )
    conn.commit()
    return cur.lastrowid


def _link_places(conn, job_id, place_ids):
    conn.executemany(
        "INSERT INTO roundup_queue_place (roundup_queue_id, place_id) VALUES (?, ?)",
        [(job_id, place_id) for place_id in place_ids],
    )
    conn.commit()


# --- database.create_roundup_job / get_roundup_job / list_roundup_jobs -----

def test_create_roundup_job_links_places(temp_db, conn):
    insert_place(conn, "p1")
    insert_place(conn, "p2")

    job = database.create_roundup_job("mexicano en palma", ["p1", "p2"])

    detail = database.get_roundup_job(job["id"])
    assert detail["tema"] == "mexicano en palma"
    assert detail["status"] == "pending"
    assert [p["place_id"] for p in detail["places"]] == ["p1", "p2"]


def test_get_roundup_job_returns_none_for_missing_id(temp_db):
    assert database.get_roundup_job(999) is None


def test_list_roundup_jobs_counts_published_places(temp_db, conn):
    insert_place(conn, "p1", publicado_en_wp=1)
    insert_place(conn, "p2", publicado_en_wp=0)
    job_id = _insert_job(conn, tema="tema x")
    _link_places(conn, job_id, ["p1", "p2"])

    jobs = database.list_roundup_jobs()

    assert len(jobs) == 1
    assert jobs[0]["place_count"] == 2
    assert jobs[0]["published_count"] == 1


# --- publication_queue.enqueue_specific_places ------------------------------

def test_enqueue_specific_places_skips_already_published(temp_db, conn):
    insert_place(conn, "a", publicado_en_wp=1)
    insert_place(conn, "b", publicado_en_wp=0)

    added = pq.enqueue_specific_places(["a", "b"])

    assert added == 1
    rows = conn.execute("SELECT place_id FROM publication_queue").fetchall()
    assert [r["place_id"] for r in rows] == ["b"]


def test_enqueue_specific_places_resets_failed_rows(temp_db, conn):
    insert_place(conn, "a", publicado_en_wp=0)
    conn.execute(
        """
        INSERT INTO publication_queue (place_id, status, attempts, last_error, created_at)
        VALUES ('a', 'failed', 3, 'boom', ?)
        """,
        (int(time.time()),),
    )
    conn.commit()

    added = pq.enqueue_specific_places(["a"])

    assert added == 1
    row = conn.execute("SELECT * FROM publication_queue WHERE place_id = 'a'").fetchone()
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert row["last_error"] is None


# --- roundup_queue._claim_next ----------------------------------------------

def test_claim_next_returns_none_when_inactive(temp_db, conn):
    _insert_job(conn)
    _set_control(conn, active=0)

    assert rq._claim_next() is None


def test_claim_next_claims_oldest_pending_without_incrementing_attempts(temp_db, conn):
    job_a = _insert_job(conn, created_at=1)
    _insert_job(conn, created_at=2)
    _set_control(conn, active=1, interval_seconds=15)

    claimed = rq._claim_next()

    assert claimed == job_a
    row = conn.execute("SELECT * FROM roundup_queue WHERE id = ?", (job_a,)).fetchone()
    assert row["status"] == "processing"
    assert row["attempts"] == 0  # solo se cuenta un intento si de verdad falla
    assert row["started_at"] is not None


def test_claim_next_deactivates_when_nothing_claimable(temp_db, conn):
    _insert_job(conn, status="pending", attempts=3, max_attempts=3)
    _set_control(conn, active=1)

    assert rq._claim_next() is None
    control = conn.execute("SELECT active FROM roundup_queue_control").fetchone()
    assert control["active"] == 0


# --- roundup_queue._run_pipeline --------------------------------------------

def test_run_pipeline_raises_not_ready_when_places_still_unpublished(temp_db, conn):
    insert_place(conn, "p1", publicado_en_wp=0)
    insert_place(conn, "p2", publicado_en_wp=1, wp_post_id=1)
    job_id = _insert_job(conn)
    _link_places(conn, job_id, ["p1", "p2"])

    try:
        rq._run_pipeline(job_id)
        assert False, "debería haber lanzado _NotReadyYet"
    except rq._NotReadyYet as exc:
        assert "1 de 2" in str(exc)


def test_run_pipeline_raises_runtime_error_when_a_place_is_stuck_failed(temp_db, conn):
    insert_place(conn, "p1", publicado_en_wp=0, name="Restaurante Atascado")
    job_id = _insert_job(conn)
    _link_places(conn, job_id, ["p1"])
    conn.execute(
        "INSERT INTO publication_queue (place_id, status, attempts, created_at) VALUES ('p1', 'failed', 3, ?)",
        (int(time.time()),),
    )
    conn.commit()

    try:
        rq._run_pipeline(job_id)
        assert False, "debería haber lanzado RuntimeError"
    except rq._NotReadyYet:
        assert False, "una ficha atascada no debe tratarse como 'esperando'"
    except RuntimeError as exc:
        assert "Restaurante Atascado" in str(exc)


def test_run_pipeline_calls_build_and_publish_when_all_published(temp_db, conn, monkeypatch):
    insert_place(conn, "p1", publicado_en_wp=1, wp_post_id=1)
    insert_place(conn, "p2", publicado_en_wp=1, wp_post_id=2)
    job_id = _insert_job(conn, tema="mexicano en palma")
    _link_places(conn, job_id, ["p1", "p2"])

    calls = {}

    def _fake_build(tema, place_ids, post_id):
        calls["tema"] = tema
        calls["place_ids"] = place_ids
        calls["post_id"] = post_id
        return {"title": "T", "url": "https://example.com/t", "post_id": 42}

    import app.api.roundups as roundups_api
    monkeypatch.setattr(roundups_api, "build_and_publish_roundup", _fake_build)

    result = rq._run_pipeline(job_id)

    assert result == {"title": "T", "url": "https://example.com/t", "post_id": 42}
    assert calls["tema"] == "mexicano en palma"
    assert set(calls["place_ids"]) == {"p1", "p2"}


# --- roundup_queue._process_once --------------------------------------------

def test_process_once_requeues_without_counting_attempt_when_not_ready(temp_db, conn, monkeypatch):
    job_id = _insert_job(conn)
    _set_control(conn, active=1)
    monkeypatch.setattr(rq, "_run_pipeline", lambda job_id: (_ for _ in ()).throw(rq._NotReadyYet("esperando 1 de 2")))

    result = rq._process_once()

    assert result == job_id
    row = conn.execute("SELECT * FROM roundup_queue WHERE id = ?", (job_id,)).fetchone()
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert row["status_detail"] == "esperando 1 de 2"


def test_process_once_marks_completed_on_success(temp_db, conn, monkeypatch):
    job_id = _insert_job(conn)
    _set_control(conn, active=1)
    monkeypatch.setattr(
        rq, "_run_pipeline",
        lambda job_id: {"title": "T", "url": "https://example.com/t", "post_id": 42},
    )

    result = rq._process_once()

    assert result == job_id
    row = conn.execute("SELECT * FROM roundup_queue WHERE id = ?", (job_id,)).fetchone()
    assert row["status"] == "completed"
    assert row["result_post_id"] == 42
    assert row["result_url"] == "https://example.com/t"
    assert row["result_title"] == "T"


def test_process_once_marks_origin_basket_as_published_on_success(temp_db, conn, monkeypatch):
    basket = database.create_basket("cesta de pasta")
    job_id = _insert_job(conn, basket_id=basket["id"])
    _set_control(conn, active=1)
    monkeypatch.setattr(
        rq, "_run_pipeline",
        lambda job_id: {"title": "T", "url": "https://example.com/t", "post_id": 42},
    )

    rq._process_once()

    updated = database.get_basket(basket["id"])
    assert updated["published_post_id"] == 42
    assert updated["published_url"] == "https://example.com/t"
    assert updated["published_title"] == "T"
    assert updated["published_at"] is not None


def test_process_once_does_not_touch_basket_when_job_has_no_basket(temp_db, conn, monkeypatch):
    basket = database.create_basket("cesta sin relacion")
    job_id = _insert_job(conn, basket_id=None)
    _set_control(conn, active=1)
    monkeypatch.setattr(
        rq, "_run_pipeline",
        lambda job_id: {"title": "T", "url": "https://example.com/t", "post_id": 42},
    )

    rq._process_once()

    untouched = database.get_basket(basket["id"])
    assert untouched["published_post_id"] is None


def test_process_once_records_error_and_counts_attempt_on_failure(temp_db, conn, monkeypatch):
    job_id = _insert_job(conn, attempts=0, max_attempts=3)
    _set_control(conn, active=1)

    def _boom(job_id):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(rq, "_run_pipeline", _boom)

    result = rq._process_once()

    assert result == job_id
    row = conn.execute("SELECT * FROM roundup_queue WHERE id = ?", (job_id,)).fetchone()
    assert row["status"] == "pending"
    assert row["attempts"] == 1
    assert "fallo simulado" in row["last_error"]


def test_process_once_fails_permanently_after_max_attempts(temp_db, conn, monkeypatch):
    job_id = _insert_job(conn, attempts=2, max_attempts=3)
    _set_control(conn, active=1)
    monkeypatch.setattr(rq, "_run_pipeline", lambda job_id: (_ for _ in ()).throw(RuntimeError("fallo simulado")))

    rq._process_once()

    row = conn.execute("SELECT * FROM roundup_queue WHERE id = ?", (job_id,)).fetchone()
    assert row["status"] == "failed"
    assert row["attempts"] == 3


# --- roundups.queue_roundup (rechazo de cestas ya publicadas) --------------

def test_queue_roundup_rejects_when_basket_already_published(temp_db, conn):
    basket = database.create_basket("cesta ya publicada")
    conn.execute(
        "UPDATE basket SET published_post_id = 99, published_url = 'https://x', published_title = 'X' WHERE id = ?",
        (basket["id"],),
    )
    conn.commit()
    insert_place(conn, "p1", publicado_en_wp=1, wp_post_id=1)
    insert_place(conn, "p2", publicado_en_wp=1, wp_post_id=2)

    data = roundups_api.RoundupRequest(tema="x", place_ids=["p1", "p2"], basket_id=basket["id"])

    with pytest.raises(HTTPException) as exc_info:
        roundups_api.queue_roundup(data)

    assert exc_info.value.status_code == 400
    assert "ya tiene un artículo publicado" in exc_info.value.detail


def test_queue_roundup_stores_basket_id_on_job(temp_db, conn, monkeypatch):
    monkeypatch.setattr(roundups_api, "start_roundup_worker", lambda: None)
    monkeypatch.setattr(roundups_api, "activate_queue", lambda: None)
    basket = database.create_basket("cesta nueva")
    insert_place(conn, "p1", publicado_en_wp=1, wp_post_id=1)
    insert_place(conn, "p2", publicado_en_wp=1, wp_post_id=2)

    data = roundups_api.RoundupRequest(tema="x", place_ids=["p1", "p2"], basket_id=basket["id"])
    job = roundups_api.queue_roundup(data)

    row = conn.execute("SELECT basket_id FROM roundup_queue WHERE id = ?", (job["id"],)).fetchone()
    assert row["basket_id"] == basket["id"]


def test_queue_roundup_rejects_second_job_while_one_is_already_active(temp_db, conn, monkeypatch):
    monkeypatch.setattr(roundups_api, "start_roundup_worker", lambda: None)
    monkeypatch.setattr(roundups_api, "activate_queue", lambda: None)
    basket = database.create_basket("cesta con trabajo en curso")
    insert_place(conn, "p1", publicado_en_wp=1, wp_post_id=1)
    insert_place(conn, "p2", publicado_en_wp=1, wp_post_id=2)
    _insert_job(conn, basket_id=basket["id"], status="pending")

    data = roundups_api.RoundupRequest(tema="x", place_ids=["p1", "p2"], basket_id=basket["id"])

    with pytest.raises(HTTPException) as exc_info:
        roundups_api.queue_roundup(data)

    assert exc_info.value.status_code == 400
    assert "ya tiene un artículo en curso" in exc_info.value.detail


def test_has_active_roundup_job_for_basket(temp_db, conn):
    basket = database.create_basket("cesta")
    assert database.has_active_roundup_job_for_basket(basket["id"]) is False

    job_id = _insert_job(conn, basket_id=basket["id"], status="pending")
    assert database.has_active_roundup_job_for_basket(basket["id"]) is True

    conn.execute("UPDATE roundup_queue SET status = 'completed' WHERE id = ?", (job_id,))
    conn.commit()
    assert database.has_active_roundup_job_for_basket(basket["id"]) is False
