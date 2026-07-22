import sqlite3

from app.models.database import DB_PATH
from app.services.openai_writer import aplicar_titulo, generar_titulo_unico


def refresh_pending_article_titles() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT DISTINCT b.place_id, b.path, p.name, b.locality
        FROM blog_article b
        JOIN place p ON p.place_id = b.place_id
        WHERE COALESCE(p.publicado_en_wp, 0) = 0
        """
    ).fetchall()
    conn.close()

    updated = 0
    skipped = 0
    for row in rows:
        try:
            with open(row["path"], "r", encoding="utf-8") as file:
                article = file.read()
            title = generar_titulo_unico(dict(row))
            refreshed = aplicar_titulo(article, title)
            if refreshed != article:
                with open(row["path"], "w", encoding="utf-8") as file:
                    file.write(refreshed)
                updated += 1
            else:
                skipped += 1
        except OSError:
            skipped += 1
    return {"updated": updated, "skipped": skipped, "total": len(rows)}
