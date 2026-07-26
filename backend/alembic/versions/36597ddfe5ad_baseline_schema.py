"""baseline schema

Replica 1:1 el esquema que crea app.models.database.init_db() hoy en
produccion (13 tablas + 2 indices de openai_usage + las 2 filas semilla de
los controles de cola). Escrita a mano, no generada por autogenerate --
ver docs/inventories/2026-07-26-sqlalchemy-alembic-baseline.md para la
justificacion completa.

Revision ID: 36597ddfe5ad
Revises:
Create Date: 2026-07-26 19:11:23.283435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36597ddfe5ad'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOCATION_COLUMNS = [
    sa.Column("country", sa.Text()),
    sa.Column("country_code", sa.Text()),
    sa.Column("region", sa.Text()),
    sa.Column("province", sa.Text()),
    sa.Column("municipality", sa.Text()),
    sa.Column("city", sa.Text()),
    sa.Column("district", sa.Text()),
    sa.Column("latitude", sa.REAL()),
    sa.Column("longitude", sa.REAL()),
    sa.Column("email", sa.Text()),
    sa.Column("email_source", sa.Text()),
    sa.Column("business_status", sa.Text()),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "search",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("query", sa.Text(), unique=True),
        sa.Column("query_hash", sa.Text(), unique=True),
    )

    op.create_table(
        "search_result",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "search_id", sa.Integer(), sa.ForeignKey("search.id"), nullable=False
        ),
        sa.Column("name", sa.Text()),
        sa.Column("address", sa.Text()),
        sa.Column("place_id", sa.Text(), nullable=False),
        sa.Column("rating", sa.REAL()),
        sa.Column("postal_code", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("website", sa.Text()),
        *[c.copy() for c in LOCATION_COLUMNS],
        sa.UniqueConstraint("search_id", "place_id"),
    )

    op.create_table(
        "place",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("search_id", sa.Integer(), sa.ForeignKey("search.id")),
        sa.Column("name", sa.Text()),
        sa.Column("address", sa.Text()),
        # Sin unique/NOT NULL a proposito: no lo es en el esquema real hoy.
        sa.Column("place_id", sa.Text()),
        sa.Column("rating", sa.REAL()),
        sa.Column("postal_code", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("website", sa.Text()),
        sa.Column("article_path", sa.Text()),
        sa.Column("publicado_en_wp", sa.Integer(), server_default=sa.text("0")),
        sa.Column("wp_post_id", sa.Integer()),
        sa.Column("tipo_de_comida", sa.Text()),
        *[c.copy() for c in LOCATION_COLUMNS],
    )
    # Indice UNIQUE detectado contra produccion (docs/inventories/
    # 2026-07-26-sqlalchemy-alembic-baseline.md): no aparece en init_db()
    # ni en el historial de git, pero existe hoy en data/places.db.
    op.create_index("idx_place_id", "place", ["place_id"], unique=True)

    op.create_table(
        "review",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("place_id", sa.Text()),
        sa.Column("author_name", sa.Text()),
        sa.Column("rating", sa.REAL()),
        sa.Column("text", sa.Text()),
        sa.Column("time", sa.Integer()),
    )

    op.create_table(
        "review_text",
        # nullable=True a proposito: la DDL real nunca declaro NOT NULL en
        # esta PK (quirk de SQLite con PKs no enteras).
        sa.Column("place_id", sa.Text(), primary_key=True, nullable=True),
        sa.Column("name", sa.Text()),
        sa.Column("address", sa.Text()),
        sa.Column("locality", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("full_text", sa.Text()),
    )

    op.create_table(
        "blog_article",
        # nullable=True en ambas por el mismo motivo que review_text arriba.
        sa.Column("place_id", sa.Text(), primary_key=True, nullable=True),
        sa.Column("lang", sa.Text(), primary_key=True, nullable=True),
        sa.Column("path", sa.Text()),
        sa.Column("locality", sa.Text()),
    )

    op.create_table(
        "place_image",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("place_id", sa.Text(), sa.ForeignKey("place.place_id")),
        sa.Column("image_path", sa.Text()),
    )

    op.create_table(
        "place_featured_image",
        sa.Column("place_id", sa.Text(), primary_key=True, nullable=True),
        sa.Column("image_path", sa.Text(), nullable=False),
    )

    op.create_table(
        "publication_queue_control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("300"),
        ),
        sa.Column("next_run_at", sa.Integer()),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_publication_queue_control_id"),
    )

    op.create_table(
        "publication_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "place_id",
            sa.Text(),
            sa.ForeignKey("place.place_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")
        ),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.Integer()),
        sa.Column("finished_at", sa.Integer()),
    )

    op.create_table(
        "repair_queue_control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("300"),
        ),
        sa.Column("next_run_at", sa.Integer()),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_repair_queue_control_id"),
    )

    op.create_table(
        "repair_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "place_id",
            sa.Text(),
            sa.ForeignKey("place.place_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")
        ),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.Integer()),
        sa.Column("finished_at", sa.Integer()),
    )

    op.create_table(
        "openai_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("place_id", sa.Text()),
        sa.Column(
            "prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "cached_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("response_id", sa.Text()),
    )
    op.create_index(
        "idx_openai_usage_created_at", "openai_usage", ["created_at"]
    )
    op.create_index("idx_openai_usage_place_id", "openai_usage", ["place_id"])

    # Filas semilla, igual que los INSERT OR IGNORE de init_db().
    op.execute(
        "INSERT OR IGNORE INTO publication_queue_control "
        "(id, active, interval_seconds, next_run_at, updated_at) "
        "VALUES (1, 0, 300, NULL, strftime('%s', 'now'))"
    )
    op.execute(
        "INSERT OR IGNORE INTO repair_queue_control "
        "(id, active, interval_seconds, next_run_at, updated_at) "
        "VALUES (1, 0, 300, NULL, strftime('%s', 'now'))"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_openai_usage_place_id", table_name="openai_usage")
    op.drop_index("idx_openai_usage_created_at", table_name="openai_usage")
    op.drop_table("openai_usage")
    op.drop_table("repair_queue")
    op.drop_table("repair_queue_control")
    op.drop_table("publication_queue")
    op.drop_table("publication_queue_control")
    op.drop_table("place_featured_image")
    op.drop_table("place_image")
    op.drop_table("blog_article")
    op.drop_table("review_text")
    op.drop_table("review")
    op.drop_index("idx_place_id", table_name="place")
    op.drop_table("place")
    op.drop_table("search_result")
    op.drop_table("search")
