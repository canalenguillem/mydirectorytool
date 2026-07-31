import logging
import os
import sqlite3
import threading
import time

from decouple import config
from unidecode import unidecode

from app.models.database import DB_PATH

logger = logging.getLogger(__name__)


_worker_thread: threading.Thread | None = None
_worker_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def enqueue_locations(
    search_term: str, country_code: str | None, limit: int
) -> int:
    now = int(time.time())
    with _connect() as conn:
        sql = """
            SELECT sl.id
            FROM seed_location sl
            LEFT JOIN seed_queue q
              ON q.seed_location_id = sl.id AND q.search_term = ?
            WHERE sl.active = 1 AND q.id IS NULL
        """
        params: list = [search_term]
        if country_code:
            sql += " AND sl.country_code = ?"
            params.append(country_code)
        sql += " ORDER BY sl.id LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.executemany(
            """
            INSERT INTO seed_queue (seed_location_id, search_term, status, created_at)
            VALUES (?, ?, 'pending', ?)
            """,
            [(row["id"], search_term, now) for row in rows],
        )
    return len(rows)


def start_queue(
    search_term: str | None = None,
    country_code: str | None = None,
    limit: int = 200,
    interval_seconds: int = 300,
) -> dict:
    search_term = search_term or config("DIRECTORY_SEARCH_TERM", default="restaurantes")
    added = enqueue_locations(search_term, country_code, limit)
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            """
            UPDATE seed_queue_control
            SET active = 1,
                interval_seconds = ?,
                next_run_at = CASE
                    WHEN active = 1 AND next_run_at IS NOT NULL THEN next_run_at
                    ELSE ?
                END,
                updated_at = ?
            WHERE id = 1
            """,
            (interval_seconds, now, now),
        )
    return {"added": added, "search_term": search_term, **get_queue_status()}


def pause_queue() -> dict:
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            "UPDATE seed_queue_control SET active = 0, updated_at = ? WHERE id = 1",
            (now,),
        )
    return get_queue_status()


def resume_queue() -> dict:
    now = int(time.time())
    with _connect() as conn:
        pending = conn.execute(
            "SELECT 1 FROM seed_queue WHERE status = 'pending' LIMIT 1"
        ).fetchone()
        conn.execute(
            """
            UPDATE seed_queue_control
            SET active = ?, next_run_at = ?, updated_at = ? WHERE id = 1
            """,
            (1 if pending else 0, now if pending else None, now),
        )
    return get_queue_status()


def retry_failed() -> dict:
    now = int(time.time())
    with _connect() as conn:
        changed = conn.execute(
            """
            UPDATE seed_queue
            SET status = 'pending', attempts = 0, last_error = NULL,
                started_at = NULL, finished_at = NULL
            WHERE status = 'failed'
            """
        ).rowcount
        if changed:
            conn.execute(
                """
                UPDATE seed_queue_control
                SET active = 1, next_run_at = ?, updated_at = ? WHERE id = 1
                """,
                (now, now),
            )
    return {"retried": changed, **get_queue_status()}


def get_queue_status() -> dict:
    with _connect() as conn:
        control = conn.execute(
            "SELECT active, interval_seconds, next_run_at FROM seed_queue_control WHERE id = 1"
        ).fetchone()
        counts = {
            row["status"]: row["total"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS total FROM seed_queue GROUP BY status"
            ).fetchall()
        }
        current = conn.execute(
            """
            SELECT q.seed_location_id, sl.name, sl.country_code, q.search_term, q.attempts
            FROM seed_queue q
            LEFT JOIN seed_location sl ON sl.id = q.seed_location_id
            WHERE q.status = 'processing'
            LIMIT 1
            """
        ).fetchone()
        recent_errors = conn.execute(
            """
            SELECT q.seed_location_id, sl.name, q.search_term, q.attempts, q.last_error
            FROM seed_queue q
            LEFT JOIN seed_location sl ON sl.id = q.seed_location_id
            WHERE q.last_error IS NOT NULL
            ORDER BY COALESCE(q.finished_at, q.started_at) DESC
            LIMIT 5
            """
        ).fetchall()

    pending = counts.get("pending", 0)
    processing = counts.get("processing", 0)
    return {
        "active": bool(control["active"]),
        "interval_seconds": control["interval_seconds"],
        "next_run_at": control["next_run_at"],
        "pending": pending,
        "processing": processing,
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
        "total": sum(counts.values()),
        "estimated_seconds": pending * control["interval_seconds"],
        "current": dict(current) if current else None,
        "recent_errors": [dict(row) for row in recent_errors],
    }


def _claim_next() -> dict | None:
    now = int(time.time())
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        control = conn.execute(
            "SELECT active, interval_seconds, next_run_at FROM seed_queue_control WHERE id = 1"
        ).fetchone()
        if not control["active"] or (control["next_run_at"] and control["next_run_at"] > now):
            conn.rollback()
            return None

        item = conn.execute(
            """
            SELECT id, seed_location_id, search_term FROM seed_queue
            WHERE status = 'pending' AND attempts < max_attempts
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
        if not item:
            conn.execute(
                "UPDATE seed_queue_control SET active = 0, next_run_at = NULL, updated_at = ? WHERE id = 1",
                (now,),
            )
            conn.commit()
            return None

        conn.execute(
            """
            UPDATE seed_queue
            SET status = 'processing', attempts = attempts + 1, started_at = ?, last_error = NULL
            WHERE id = ?
            """,
            (now, item["id"]),
        )
        conn.execute(
            """
            UPDATE seed_queue_control
            SET next_run_at = ?, updated_at = ? WHERE id = 1
            """,
            (now + control["interval_seconds"], now),
        )
        conn.commit()
        return {
            "queue_id": item["id"],
            "seed_location_id": item["seed_location_id"],
            "search_term": item["search_term"],
        }
    finally:
        conn.close()


def _get_seed_location(seed_location_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, country_code, name, region FROM seed_location WHERE id = ?",
            (seed_location_id,),
        ).fetchone()
    return dict(row)


def _run_pipeline(seed_location_id: int, search_term: str) -> dict:
    from app.models.database import get_or_create_search_with_candidates, save_search_result
    from app.services.google_places_new import discover_candidates, normalize_candidate
    from app.services.place_ranking import select_top_candidates

    location = _get_seed_location(seed_location_id)
    query = unidecode(f"{search_term} en {location['name']}".strip())

    raw = discover_candidates(
        query,
        max_pages=int(os.environ.get("GOOGLE_SEED_MAX_PAGES", "3")),
        seed_location_id=seed_location_id,
        country_code=location["country_code"],
        directory_search_term=search_term,
    )
    candidates = [normalize_candidate(place) for place in raw]
    min_ratings = int(os.environ.get("GOOGLE_SEED_MIN_USER_RATINGS", "15"))
    top = select_top_candidates(candidates, top_n=20, min_user_ratings=min_ratings)

    places = get_or_create_search_with_candidates(query, top)

    autosave = os.environ.get("SEED_AUTOSAVE", "true").lower() == "true"
    saved = 0
    if autosave:
        for place in places:
            if save_search_result(place["place_id"]):
                saved += 1

    return {"found": len(candidates), "top": len(top), "saved": saved}


def _finish(queue_id: int, found: int | None = None, saved: int | None = None, error: str | None = None) -> None:
    now = int(time.time())
    with _connect() as conn:
        row = conn.execute(
            "SELECT attempts, max_attempts FROM seed_queue WHERE id = ?", (queue_id,)
        ).fetchone()
        if error and row["attempts"] < row["max_attempts"]:
            status = "pending"
        elif error:
            status = "failed"
        else:
            status = "completed"
        conn.execute(
            """
            UPDATE seed_queue
            SET status = ?, last_error = ?, places_found = ?, places_saved = ?, finished_at = ?
            WHERE id = ?
            """,
            (status, error, found, saved, now, queue_id),
        )


def _process_once() -> dict | None:
    """Reclama y procesa un elemento de la cola. Devuelve el item procesado,
    o None si no había nada que hacer. Extraído de _worker() para poder
    testear el manejo de errores sin el bucle infinito (mismo patrón que
    publication_queue._process_once)."""
    item = _claim_next()
    if item:
        try:
            result = _run_pipeline(item["seed_location_id"], item["search_term"])
        except Exception as exc:
            logger.exception(f"Fallo procesando seed_location {item['seed_location_id']}")
            _finish(item["queue_id"], error=str(exc)[:2000])
        else:
            _finish(item["queue_id"], found=result["found"], saved=result["saved"])
    return item


def _worker() -> None:
    while True:
        _process_once()
        time.sleep(2)


def start_worker() -> None:
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        with _connect() as conn:
            conn.execute(
                "UPDATE seed_queue SET status = 'pending' WHERE status = 'processing'"
            )
        _worker_thread = threading.Thread(target=_worker, name="seed-queue", daemon=True)
        _worker_thread.start()
