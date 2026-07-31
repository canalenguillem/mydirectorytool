import logging
import sqlite3
import threading
import time

from app.models.database import DB_PATH

logger = logging.getLogger(__name__)


_worker_thread: threading.Thread | None = None
_worker_lock = threading.Lock()


class _NotReadyYet(Exception):
    """Alguna ficha de la cesta todavía no está publicada, pero sigue en
    camino (encolada en publication_queue) -- no es un fallo del trabajo,
    solo hay que esperar al siguiente tick."""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def activate_queue() -> None:
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            """
            UPDATE roundup_queue_control
            SET active = 1,
                next_run_at = CASE
                    WHEN active = 1 AND next_run_at IS NOT NULL THEN next_run_at
                    ELSE ?
                END,
                updated_at = ?
            WHERE id = 1
            """,
            (now, now),
        )


def get_queue_status() -> dict:
    with _connect() as conn:
        control = conn.execute(
            "SELECT active, interval_seconds, next_run_at FROM roundup_queue_control WHERE id = 1"
        ).fetchone()
        counts = {row["status"]: row["total"] for row in conn.execute(
            "SELECT status, COUNT(*) AS total FROM roundup_queue GROUP BY status"
        ).fetchall()}
        current = conn.execute(
            "SELECT id, tema, status_detail, attempts FROM roundup_queue WHERE status = 'processing' LIMIT 1"
        ).fetchone()

    return {
        "active": bool(control["active"]),
        "interval_seconds": control["interval_seconds"],
        "next_run_at": control["next_run_at"],
        "pending": counts.get("pending", 0),
        "processing": counts.get("processing", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
        "current": dict(current) if current else None,
    }


def _claim_next() -> int | None:
    now = int(time.time())
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        control = conn.execute(
            "SELECT active, interval_seconds, next_run_at FROM roundup_queue_control WHERE id = 1"
        ).fetchone()
        if not control["active"] or (control["next_run_at"] and control["next_run_at"] > now):
            conn.rollback()
            return None

        item = conn.execute(
            """
            SELECT id FROM roundup_queue
            WHERE status = 'pending' AND attempts < max_attempts
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
        if not item:
            conn.execute(
                "UPDATE roundup_queue_control SET active = 0, next_run_at = NULL, updated_at = ? WHERE id = 1",
                (now,),
            )
            conn.commit()
            return None

        conn.execute(
            "UPDATE roundup_queue SET status = 'processing', started_at = ? WHERE id = ?",
            (now, item["id"]),
        )
        conn.execute(
            "UPDATE roundup_queue_control SET next_run_at = ?, updated_at = ? WHERE id = 1",
            (now + control["interval_seconds"], now),
        )
        conn.commit()
        return item["id"]
    finally:
        conn.close()


def _stuck_place_names(place_ids: list[str]) -> list[str]:
    """Nombres de las fichas dadas que ya agotaron sus intentos en
    publication_queue -- si alguna está aquí, esperar más ticks no va a
    arreglarlo solo, hay que fallar el trabajo con un mensaje claro en vez
    de reintentar publicar sin límite."""
    if not place_ids:
        return []
    with _connect() as conn:
        placeholders = ",".join("?" for _ in place_ids)
        rows = conn.execute(
            f"""
            SELECT p.name
            FROM publication_queue q
            JOIN place p ON p.place_id = q.place_id
            WHERE q.place_id IN ({placeholders}) AND q.status = 'failed'
            """,
            place_ids,
        ).fetchall()
    return [row["name"] for row in rows]


def _run_pipeline(job_id: int) -> dict:
    from app.models.database import get_roundup_job

    job = get_roundup_job(job_id)
    if not job:
        raise RuntimeError("El trabajo ya no existe")

    unpublished = [p for p in job["places"] if not p["publicado_en_wp"] or not p["wp_post_id"]]
    if unpublished:
        stuck = _stuck_place_names([p["place_id"] for p in unpublished])
        if stuck:
            raise RuntimeError(
                "No se pudieron publicar automáticamente: " + ", ".join(stuck)
                + ". Revisa la cola de publicación (Automatización) y vuelve a generar el artículo."
            )
        raise _NotReadyYet(
            f"Esperando a publicar {len(unpublished)} de {len(job['places'])} fichas"
        )

    from app.api.roundups import build_and_publish_roundup

    return build_and_publish_roundup(
        job["tema"], [p["place_id"] for p in job["places"]], job["post_id"]
    )


def _finish(job_id: int, error: str | None = None, result: dict | None = None) -> None:
    now = int(time.time())
    with _connect() as conn:
        if error:
            row = conn.execute(
                "SELECT attempts, max_attempts FROM roundup_queue WHERE id = ?", (job_id,)
            ).fetchone()
            attempts = row["attempts"] + 1
            status = "pending" if attempts < row["max_attempts"] else "failed"
            conn.execute(
                """
                UPDATE roundup_queue
                SET status = ?, attempts = ?, last_error = ?, status_detail = NULL, finished_at = ?
                WHERE id = ?
                """,
                (status, attempts, error, now, job_id),
            )
        else:
            conn.execute(
                """
                UPDATE roundup_queue
                SET status = 'completed', last_error = NULL, status_detail = NULL,
                    result_post_id = ?, result_url = ?, result_title = ?, finished_at = ?
                WHERE id = ?
                """,
                (result["post_id"], result["url"], result["title"], now, job_id),
            )
            job = conn.execute(
                "SELECT basket_id FROM roundup_queue WHERE id = ?", (job_id,)
            ).fetchone()
            if job and job["basket_id"]:
                conn.execute(
                    """
                    UPDATE basket
                    SET published_post_id = ?, published_url = ?, published_title = ?, published_at = ?
                    WHERE id = ?
                    """,
                    (result["post_id"], result["url"], result["title"], now, job["basket_id"]),
                )


def _requeue_waiting(job_id: int, note: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE roundup_queue SET status = 'pending', status_detail = ?, started_at = NULL WHERE id = ?",
            (note, job_id),
        )


def _process_once() -> int | None:
    """Reclama y procesa un trabajo de la cola. Devuelve su id, o None si
    no había nada que hacer. Extraído de _worker() para poder testear el
    manejo de errores sin el bucle infinito."""
    job_id = _claim_next()
    if not job_id:
        return None
    try:
        result = _run_pipeline(job_id)
    except _NotReadyYet as exc:
        _requeue_waiting(job_id, str(exc))
    except Exception as exc:
        logger.exception(f"Fallo generando el artículo del trabajo {job_id}")
        _finish(job_id, error=str(exc)[:2000])
    else:
        _finish(job_id, result=result)
    return job_id


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
                "UPDATE roundup_queue SET status = 'pending' WHERE status = 'processing'"
            )
        _worker_thread = threading.Thread(target=_worker, name="roundup-queue", daemon=True)
        _worker_thread.start()
