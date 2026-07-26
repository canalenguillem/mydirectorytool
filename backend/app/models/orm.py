"""Modelos SQLAlchemy que reflejan fielmente el esquema actual de SQLite.

Este fichero NO se importa desde `app.main` ni desde ningun router o
servicio. Es la fuente de verdad que usa Alembic (`backend/alembic/env.py`)
para generar y verificar migraciones. El esquema real en produccion lo sigue
creando `app.models.database.init_db()`, sin cambios.

Los modelos reproducen a proposito las particularidades reales del esquema,
no una version idealizada. Verificado con `alembic revision --autogenerate`
contra una copia de `data/places.db` (ver
docs/inventories/2026-07-26-sqlalchemy-alembic-baseline.md):

- `Place.place_id` no es NOT NULL en la columna, pero SI tiene un indice
  UNIQUE (`idx_place_id`) en la base real -- creado en algun momento
  directamente contra produccion, sin dejar rastro en `init_db()`, en
  ningun otro fichero del repo ni en el historial de git. Se modela aqui
  el indice unico para reflejar la realidad, pero la columna sigue sin
  `nullable=False` porque tampoco lo es hoy.
- `BlogArticle.place_id`/`lang`, `ReviewText.place_id` y
  `PlaceFeaturedImage.place_id` son parte de su PRIMARY KEY pero la DDL
  real nunca declaro `NOT NULL` en ellas (quirk de SQLite: una PK no
  entera no fuerza NOT NULL salvo que se declare explicitamente). Se
  fuerza aqui `nullable=True` para no anadir una restriccion que no existe
  hoy en produccion.
- Las columnas de `LOCATION_COLUMNS` se anadieron con `ALTER TABLE` via
  `_ensure_columns()`; se modelan igual que cualquier columna nullable
  normal, porque el resultado final es el mismo sea cual sea su origen.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    REAL,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Search(Base):
    __tablename__ = "search"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str | None] = mapped_column(Text, unique=True)
    query_hash: Mapped[str | None] = mapped_column(Text, unique=True)


class SearchResult(Base):
    __tablename__ = "search_result"
    __table_args__ = (UniqueConstraint("search_id", "place_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("search.id"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    place_id: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[float | None] = mapped_column(REAL)
    postal_code: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    # LOCATION_COLUMNS (anadidas via _ensure_columns / ALTER TABLE)
    country: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(REAL)
    longitude: Mapped[float | None] = mapped_column(REAL)
    email: Mapped[str | None] = mapped_column(Text)
    email_source: Mapped[str | None] = mapped_column(Text)
    business_status: Mapped[str | None] = mapped_column(Text)


class Place(Base):
    __tablename__ = "place"
    __table_args__ = (Index("idx_place_id", "place_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("search.id"))
    name: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    # Columna sin NOT NULL, pero con indice UNIQUE -- ver docstring del modulo.
    place_id: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[float | None] = mapped_column(REAL)
    postal_code: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    article_path: Mapped[str | None] = mapped_column(Text)
    publicado_en_wp: Mapped[int | None] = mapped_column(
        Integer, server_default=text("0")
    )
    wp_post_id: Mapped[int | None] = mapped_column(Integer)
    tipo_de_comida: Mapped[str | None] = mapped_column(Text)
    # LOCATION_COLUMNS (anadidas via _ensure_columns / ALTER TABLE)
    country: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(REAL)
    longitude: Mapped[float | None] = mapped_column(REAL)
    email: Mapped[str | None] = mapped_column(Text)
    email_source: Mapped[str | None] = mapped_column(Text)
    business_status: Mapped[str | None] = mapped_column(Text)


class Review(Base):
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_id: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[float | None] = mapped_column(REAL)
    text_: Mapped[str | None] = mapped_column("text", Text)
    time: Mapped[int | None] = mapped_column(Integer)


class ReviewText(Base):
    __tablename__ = "review_text"

    place_id: Mapped[str] = mapped_column(Text, primary_key=True, nullable=True)
    name: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    locality: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)


class BlogArticle(Base):
    __tablename__ = "blog_article"
    __table_args__ = (PrimaryKeyConstraint("place_id", "lang"),)

    place_id: Mapped[str] = mapped_column(Text, nullable=True)
    lang: Mapped[str] = mapped_column(Text, nullable=True)
    path: Mapped[str | None] = mapped_column(Text)
    locality: Mapped[str | None] = mapped_column(Text)


class PlaceImage(Base):
    __tablename__ = "place_image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_id: Mapped[str | None] = mapped_column(Text, ForeignKey("place.place_id"))
    image_path: Mapped[str | None] = mapped_column(Text)


class PlaceFeaturedImage(Base):
    __tablename__ = "place_featured_image"

    place_id: Mapped[str] = mapped_column(Text, primary_key=True, nullable=True)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)


class PublicationQueueControl(Base):
    __tablename__ = "publication_queue_control"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_publication_queue_control_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("300")
    )
    next_run_at: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)


class PublicationQueue(Base):
    __tablename__ = "publication_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_id: Mapped[str] = mapped_column(
        Text, ForeignKey("place.place_id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pending'")
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("3")
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[int | None] = mapped_column(Integer)
    finished_at: Mapped[int | None] = mapped_column(Integer)


class RepairQueueControl(Base):
    __tablename__ = "repair_queue_control"
    __table_args__ = (CheckConstraint("id = 1", name="ck_repair_queue_control_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("300")
    )
    next_run_at: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)


class RepairQueue(Base):
    __tablename__ = "repair_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_id: Mapped[str] = mapped_column(
        Text, ForeignKey("place.place_id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pending'")
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("3")
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[int | None] = mapped_column(Integer)
    finished_at: Mapped[int | None] = mapped_column(Integer)


class OpenAIUsage(Base):
    __tablename__ = "openai_usage"
    __table_args__ = (
        Index("idx_openai_usage_created_at", "created_at"),
        Index("idx_openai_usage_place_id", "place_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    place_id: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cached_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    response_id: Mapped[str | None] = mapped_column(Text)
