import logging
import sqlite3
import time

from app.models.database import DB_PATH

logger = logging.getLogger(__name__)


def record_google_places_usage(
    operation: str,
    endpoint_version: str,
    field_mask: str | None = None,
    query: str | None = None,
    seed_location_id: int | None = None,
    country_code: str | None = None,
    directory_search_term: str | None = None,
    result_count: int | None = None,
    status: str | None = None,
    place_id: str | None = None,
) -> None:
    """Persist Google Places API usage without ever interrupting the caller."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO google_places_usage (
                    created_at, operation, endpoint_version, field_mask, query,
                    seed_location_id, country_code, directory_search_term,
                    result_count, status, place_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(time.time()),
                    operation,
                    endpoint_version,
                    field_mask,
                    query,
                    seed_location_id,
                    country_code,
                    directory_search_term,
                    result_count,
                    status,
                    place_id,
                ),
            )
    except Exception as exc:
        logger.warning(f"No se pudo registrar el uso de Google Places: {exc}")


def get_google_places_usage_summary(days: int = 30) -> dict:
    days = max(1, min(days, 3650))
    since = int(time.time()) - days * 86400
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(
            """
            SELECT COUNT(*) AS requests,
                   COALESCE(SUM(result_count), 0) AS results
            FROM google_places_usage
            WHERE created_at >= ?
            """,
            (since,),
        ).fetchone()
        breakdown = conn.execute(
            """
            SELECT operation, COUNT(*) AS requests,
                   COALESCE(SUM(result_count), 0) AS results
            FROM google_places_usage
            WHERE created_at >= ?
            GROUP BY operation
            ORDER BY requests DESC
            """,
            (since,),
        ).fetchall()

    return {
        "days": days,
        **dict(total),
        "breakdown": [dict(row) for row in breakdown],
    }
