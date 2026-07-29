"""review and place_image unique constraints

Añade las restricciones de integridad que faltaban (Fase 1 del roadmap,
docs/inventories/2026-07-26-integrity-and-logging.md): review tenía 81
filas duplicadas reales en producción, así que primero se desduplica y
luego se crean los índices únicos. place_image ya estaba limpia.

Revision ID: ef082d3b0c89
Revises: 36597ddfe5ad
Create Date: 2026-07-29 19:39:30.895491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef082d3b0c89'
down_revision: Union[str, Sequence[str], None] = '36597ddfe5ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Desduplicar antes de indexar. Idempotente: en una base ya limpia no
    # borra nada (no hay grupos con más de una fila).
    op.execute(
        """
        DELETE FROM review
        WHERE id NOT IN (
            SELECT MIN(id) FROM review
            GROUP BY place_id, author_name, text, time
        )
        """
    )
    op.create_index(
        "idx_review_unique", "review",
        ["place_id", "author_name", "text", "time"], unique=True,
    )
    op.create_index(
        "idx_place_image_unique", "place_image",
        ["place_id", "image_path"], unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # No restaura las filas de review borradas en el upgrade -- el dedup
    # no es reversible, solo se revierte la restricción.
    op.drop_index("idx_place_image_unique", table_name="place_image")
    op.drop_index("idx_review_unique", table_name="review")
