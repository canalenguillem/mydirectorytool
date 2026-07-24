import sqlite3
import time
from typing import Any

from app.models.database import DB_PATH


def record_openai_usage(
    response: Any,
    operation: str,
    place_id: str | None = None,
) -> None:
    """Persist token usage without ever interrupting the user operation."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(
            getattr(usage, "total_tokens", prompt_tokens + completion_tokens)
            or prompt_tokens + completion_tokens
        )
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        cached_tokens = int(getattr(prompt_details, "cached_tokens", 0) or 0)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO openai_usage (
                    created_at, operation, model, place_id,
                    prompt_tokens, completion_tokens, total_tokens,
                    cached_tokens, response_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(time.time()),
                    operation,
                    str(getattr(response, "model", "") or "desconocido"),
                    place_id,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cached_tokens,
                    getattr(response, "id", None),
                ),
            )
    except Exception as exc:
        print(f"[WARN] No se pudo registrar el uso de OpenAI: {exc}")


def get_usage_summary(days: int = 30) -> dict:
    days = max(1, min(days, 3650))
    since = int(time.time()) - days * 86400
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(
            """
            SELECT COUNT(*) AS requests,
                   COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                   COALESCE(SUM(total_tokens), 0) AS total_tokens,
                   COALESCE(SUM(cached_tokens), 0) AS cached_tokens
            FROM openai_usage
            WHERE created_at >= ?
            """,
            (since,),
        ).fetchone()
        breakdown = conn.execute(
            """
            SELECT operation, model, COUNT(*) AS requests,
                   COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                   COALESCE(SUM(total_tokens), 0) AS total_tokens
            FROM openai_usage
            WHERE created_at >= ?
            GROUP BY operation, model
            ORDER BY total_tokens DESC
            """,
            (since,),
        ).fetchall()

    return {
        "days": days,
        **dict(total),
        "breakdown": [dict(row) for row in breakdown],
    }
