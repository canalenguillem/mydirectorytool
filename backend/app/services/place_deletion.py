from pathlib import Path
import sqlite3

import requests
from fastapi import HTTPException

from app.models.database import DATA_DIR, DB_PATH
from app.services.wordpress import AUTH, REQUEST_TIMEOUT, WP_URL


def _wordpress_media_ids(post_id: int) -> set[int]:
    post_response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/restaurante/{post_id}",
        auth=AUTH,
        params={"context": "edit", "_fields": "id,featured_media"},
        timeout=REQUEST_TIMEOUT,
    )
    if post_response.status_code == 404:
        return set()
    if post_response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"WordPress no permite comprobar el post {post_id}",
        )

    media_ids: set[int] = set()
    featured_media = post_response.json().get("featured_media")
    if featured_media:
        media_ids.add(int(featured_media))

    page = 1
    while True:
        media_response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/media",
            auth=AUTH,
            params={"parent": post_id, "per_page": 100, "page": page, "_fields": "id"},
            timeout=REQUEST_TIMEOUT,
        )
        if media_response.status_code == 400 and page > 1:
            break
        if media_response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"WordPress no permite obtener las imágenes del post {post_id}",
            )
        items = media_response.json()
        media_ids.update(int(item["id"]) for item in items)
        total_pages = int(media_response.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1
    return media_ids


def _delete_wordpress(post_id: int) -> list[int]:
    media_ids = _wordpress_media_ids(post_id)
    deleted_media: list[int] = []
    for media_id in sorted(media_ids):
        response = requests.delete(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            auth=AUTH,
            params={"force": "true"},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code not in {200, 404, 410}:
            raise HTTPException(
                status_code=502,
                detail=f"No se pudo borrar la imagen {media_id} de WordPress",
            )
        deleted_media.append(media_id)

    response = requests.delete(
        f"{WP_URL}/wp-json/wp/v2/restaurante/{post_id}",
        auth=AUTH,
        params={"force": "true"},
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code not in {200, 404, 410}:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo borrar el restaurante {post_id} de WordPress",
        )
    return deleted_media


def _delete_local_files(paths: set[str]) -> list[str]:
    data_root = Path(DATA_DIR).resolve()
    deleted: list[str] = []
    candidate_directories: set[Path] = set()

    for raw_path in paths:
        if not raw_path:
            continue
        raw = Path(raw_path)
        path = (raw if raw.is_absolute() else data_root / raw).resolve()
        if not path.is_relative_to(data_root):
            raise HTTPException(
                status_code=500,
                detail=f"Ruta local no permitida para borrado: {raw_path}",
            )
        candidates = {path}
        optimized = path.parent / ".wordpress" / f"{path.stem}.jpg"
        candidates.add(optimized)
        for candidate in candidates:
            if candidate.is_file():
                candidate.unlink()
                deleted.append(str(candidate))
                candidate_directories.add(candidate.parent)

    for directory in sorted(candidate_directories, key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
            parent = directory.parent
            if parent != data_root:
                parent.rmdir()
        except OSError:
            pass
    return deleted


def delete_place_completely(place_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    place = conn.execute(
        "SELECT name, publicado_en_wp, wp_post_id FROM place WHERE place_id = ?",
        (place_id,),
    ).fetchone()
    if not place:
        conn.close()
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    queue_item = conn.execute(
        "SELECT status FROM publication_queue WHERE place_id = ?", (place_id,)
    ).fetchone()
    if queue_item and queue_item["status"] == "processing":
        conn.close()
        raise HTTPException(
            status_code=409,
            detail="Este restaurante se está procesando; pausa la cola y vuelve a intentarlo",
        )

    local_paths = {
        row[0]
        for row in conn.execute(
            "SELECT image_path FROM place_image WHERE place_id = ?", (place_id,)
        ).fetchall()
        if row[0]
    }
    local_paths.update(
        row[0]
        for row in conn.execute(
            "SELECT image_path FROM place_featured_image WHERE place_id = ?", (place_id,)
        ).fetchall()
        if row[0]
    )
    local_paths.update(
        row[0]
        for row in conn.execute(
            "SELECT path FROM blog_article WHERE place_id = ?", (place_id,)
        ).fetchall()
        if row[0]
    )
    conn.close()

    deleted_media: list[int] = []
    post_id = place["wp_post_id"]
    if post_id:
        deleted_media = _delete_wordpress(int(post_id))

    deleted_files = _delete_local_files(local_paths)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for table in (
            "publication_queue",
            "place_featured_image",
            "place_image",
            "blog_article",
            "review",
            "review_text",
        ):
            conn.execute(f"DELETE FROM {table} WHERE place_id = ?", (place_id,))
        conn.execute("DELETE FROM place WHERE place_id = ?", (place_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "message": f"{place['name']} se ha eliminado completamente",
        "wordpress_post_id": post_id,
        "deleted_media": deleted_media,
        "deleted_local_files": len(deleted_files),
    }
