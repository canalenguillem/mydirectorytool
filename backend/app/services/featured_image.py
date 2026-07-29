import logging
import sqlite3
from app.models.database import DB_PATH

logger = logging.getLogger(__name__)


def set_featured_image(place_id: str, image_path: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO place_featured_image (place_id, image_path)
        VALUES (?, ?)
        ON CONFLICT(place_id) DO UPDATE SET image_path=excluded.image_path
    """, (place_id, image_path))
    conn.commit()
    conn.close()
    logger.info(f"Imatge destacada registrada per {place_id}")
