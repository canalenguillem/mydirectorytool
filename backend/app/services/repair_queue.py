import sqlite3
import threading
import time
import traceback

from app.models.database import DB_PATH


_worker_thread: threading.Thread | None = None
_worker_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _incomplete_place_ids(limit: int) -> list[str]:
    from app.models.database import list_all_places

    return [
        place["place_id"]
        for place in list_all_places()
        if place["is_incomplete"]
    ][:limit]


def enqueue_incomplete_places(limit: int) -> int:
    now = int(time.time())
    place_ids = _incomplete_place_ids(limit)
    added = 0
    with _connect() as conn:
        for place_id in place_ids:
            existing = conn.execute(
                "SELECT status FROM repair_queue WHERE place_id = ?",
                (place_id,),
            ).fetchone()
            if existing and existing["status"] in ("pending", "processing"):
                continue
            if existing:
                conn.execute(
                    """
                    UPDATE repair_queue
                    SET status = 'pending', attempts = 0, last_error = NULL,
                        created_at = ?, started_at = NULL, finished_at = NULL
                    WHERE place_id = ?
                    """,
                    (now, place_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO repair_queue (place_id, status, created_at)
                    VALUES (?, 'pending', ?)
                    """,
                    (place_id, now),
                )
            added += 1
    return added


def start_queue(limit: int, interval_seconds: int = 300) -> dict:
    added = enqueue_incomplete_places(limit)
    now = int(time.time())
    with _connect() as conn:
        pending = conn.execute(
            "SELECT 1 FROM repair_queue WHERE status = 'pending' LIMIT 1"
        ).fetchone()
        conn.execute(
            """
            UPDATE repair_queue_control
            SET active = ?, interval_seconds = ?, next_run_at = ?,
                updated_at = ? WHERE id = 1
            """,
            (1 if pending else 0, interval_seconds, now if pending else None, now),
        )
    return {"added": added, **get_queue_status()}


def pause_queue() -> dict:
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            "UPDATE repair_queue_control SET active = 0, updated_at = ? WHERE id = 1",
            (now,),
        )
    return get_queue_status()


def resume_queue() -> dict:
    now = int(time.time())
    with _connect() as conn:
        pending = conn.execute(
            "SELECT 1 FROM repair_queue WHERE status = 'pending' LIMIT 1"
        ).fetchone()
        conn.execute(
            """
            UPDATE repair_queue_control
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
            UPDATE repair_queue
            SET status = 'pending', attempts = 0, last_error = NULL,
                started_at = NULL, finished_at = NULL
            WHERE status = 'failed'
            """
        ).rowcount
        if changed:
            conn.execute(
                """
                UPDATE repair_queue_control
                SET active = 1, next_run_at = ?, updated_at = ? WHERE id = 1
                """,
                (now, now),
            )
    return {"retried": changed, **get_queue_status()}


def get_queue_status() -> dict:
    with _connect() as conn:
        control = conn.execute(
            "SELECT active, interval_seconds, next_run_at FROM repair_queue_control WHERE id = 1"
        ).fetchone()
        counts = {
            row["status"]: row["total"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS total FROM repair_queue GROUP BY status"
            ).fetchall()
        }
        current = conn.execute(
            """
            SELECT q.place_id, p.name, q.attempts
            FROM repair_queue q
            LEFT JOIN place p ON p.place_id = q.place_id
            WHERE q.status = 'processing'
            LIMIT 1
            """
        ).fetchone()
        recent_errors = conn.execute(
            """
            SELECT q.place_id, p.name, q.attempts, q.last_error
            FROM repair_queue q
            LEFT JOIN place p ON p.place_id = q.place_id
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


def _claim_next() -> str | None:
    now = int(time.time())
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        control = conn.execute(
            "SELECT active, interval_seconds, next_run_at FROM repair_queue_control WHERE id = 1"
        ).fetchone()
        if not control["active"] or (
            control["next_run_at"] and control["next_run_at"] > now
        ):
            conn.rollback()
            return None

        item = conn.execute(
            """
            SELECT id, place_id FROM repair_queue
            WHERE status = 'pending' AND attempts < max_attempts
            ORDER BY id LIMIT 1
            """
        ).fetchone()
        if not item:
            conn.execute(
                """
                UPDATE repair_queue_control
                SET active = 0, next_run_at = NULL, updated_at = ? WHERE id = 1
                """,
                (now,),
            )
            conn.commit()
            return None

        conn.execute(
            """
            UPDATE repair_queue
            SET status = 'processing', attempts = attempts + 1,
                started_at = ?, last_error = NULL WHERE id = ?
            """,
            (now, item["id"]),
        )
        conn.execute(
            """
            UPDATE repair_queue_control
            SET next_run_at = ?, updated_at = ? WHERE id = 1
            """,
            (now + control["interval_seconds"], now),
        )
        conn.commit()
        return item["place_id"]
    finally:
        conn.close()


def _repair_place(place_id: str) -> None:
    from app.api.blog import acf_fields_from_data, full_publish
    from app.models.database import (
        enrich_place_details,
        get_all_images_for_place,
        get_or_create_article,
        get_or_create_review_info,
        get_article_data,
        list_all_places,
        set_place_food_type,
    )
    from app.services.comida_classifier import detectar_tipo_comida
    from app.services.featured_image import set_featured_image
    from app.services.openai_writer import generar_articulo_blog
    from app.services.place_images import download_all_place_photos
    from app.services.wordpress import guardar_campos_acf

    place = next(p for p in list_all_places() if p["place_id"] == place_id)
    flags = set(place["incomplete_fields"])

    if "wordpress_link" in flags:
        info = get_or_create_review_info(place_id)
        get_or_create_article(info, "es", generar_articulo_blog)

    if flags.intersection({"contact", "location"}):
        enrich_place_details(place_id)

    data = get_article_data(place_id)
    if "food_type" in flags and data and data.get("content"):
        food_type = detectar_tipo_comida(data["content"])
        if food_type:
            set_place_food_type(place_id, food_type)

    if "images" in flags:
        image_paths = download_all_place_photos(place_id)
        if not image_paths:
            raise RuntimeError("No se encontraron imágenes para el restaurante")
        with _connect() as conn:
            for image_path in image_paths:
                exists = conn.execute(
                    """
                    SELECT 1 FROM place_image
                    WHERE place_id = ? AND image_path = ?
                    """,
                    (place_id, image_path),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO place_image (place_id, image_path) VALUES (?, ?)",
                        (place_id, image_path),
                    )
        if not get_all_images_for_place(place_id):
            raise RuntimeError("Las imágenes no se pudieron registrar")
        set_featured_image(place_id, get_all_images_for_place(place_id)[0])

    data = get_article_data(place_id)
    if not data:
        raise RuntimeError("No se encontraron los datos del restaurante")

    if "wordpress_link" in flags:
        result = full_publish(place_id)
        if result.get("error") or not result.get("post_id"):
            raise RuntimeError(result.get("error") or "WordPress no devolvió un ID")
    elif data.get("publicado_en_wp") and data.get("wp_post_id"):
        if not guardar_campos_acf(
            int(data["wp_post_id"]),
            acf_fields_from_data(data),
        ):
            raise RuntimeError("WordPress no aceptó los campos ACF")


def _finish(place_id: str, error: str | None = None) -> None:
    now = int(time.time())
    with _connect() as conn:
        row = conn.execute(
            "SELECT attempts, max_attempts FROM repair_queue WHERE place_id = ?",
            (place_id,),
        ).fetchone()
        status = (
            "pending"
            if error and row["attempts"] < row["max_attempts"]
            else "failed"
            if error
            else "completed"
        )
        conn.execute(
            """
            UPDATE repair_queue
            SET status = ?, last_error = ?, finished_at = ? WHERE place_id = ?
            """,
            (status, error, now, place_id),
        )


def _worker() -> None:
    while True:
        place_id = _claim_next()
        if place_id:
            try:
                _repair_place(place_id)
            except Exception as exc:
                traceback.print_exc()
                _finish(place_id, str(exc)[:2000])
            else:
                _finish(place_id)
        time.sleep(2)


def start_worker() -> None:
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        with _connect() as conn:
            conn.execute(
                "UPDATE repair_queue SET status = 'pending' WHERE status = 'processing'"
            )
        _worker_thread = threading.Thread(
            target=_worker,
            name="repair-queue",
            daemon=True,
        )
        _worker_thread.start()
