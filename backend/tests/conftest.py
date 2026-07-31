"""Fixtures compartidas. Cada test corre contra un SQLite temporal propio
(tmp_path) -- nunca contra data/places.db. Si algo se sale de esa
garantia, que falle por "no existe el fichero", no en silencio.
"""

import sqlite3
import time

import pytest

from app.models import database
from app.services import google_places_usage, publication_queue, repair_queue, roundup_queue, seed_queue


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "places_test.db")

    monkeypatch.setattr(database, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(publication_queue, "DB_PATH", db_path)
    monkeypatch.setattr(repair_queue, "DB_PATH", db_path)
    monkeypatch.setattr(seed_queue, "DB_PATH", db_path)
    monkeypatch.setattr(google_places_usage, "DB_PATH", db_path)
    monkeypatch.setattr(roundup_queue, "DB_PATH", db_path)

    database.init_db()
    return db_path


@pytest.fixture
def conn(temp_db):
    connection = sqlite3.connect(temp_db)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def insert_place(connection: sqlite3.Connection, place_id: str, **overrides) -> None:
    """Inserta una fila `place` con contacto/ubicacion/tipo de comida
    completos por defecto (no publicada). OJO: `is_incomplete` en
    database.list_all_places() tambien exige al menos una imagen cuyo
    fichero exista en disco -- sin llamar ademas a add_fake_image(), la
    ficha sale incompleta por falta de imagenes aunque el resto este
    relleno. Los tests sobreescriben solo los campos que necesitan para
    forzar un estado concreto."""
    row = {
        "place_id": place_id,
        "name": overrides.get("name", f"Restaurante {place_id}"),
        "address": "Calle Falsa 123",
        "phone": "+34 600 000 000",
        "website": "https://example.com",
        "email": "",
        "publicado_en_wp": 0,
        "wp_post_id": None,
        "article_path": None,
        "tipo_de_comida": "mediterránea",
        "municipality": "Palma",
        "city": "Palma",
        "postal_code": "07001",
        "country_code": "ES",
        "latitude": 39.5,
        "longitude": 2.6,
    }
    row.update(overrides)
    connection.execute(
        """
        INSERT INTO place (
            place_id, name, address, phone, website, email,
            publicado_en_wp, wp_post_id, article_path, tipo_de_comida,
            municipality, city, postal_code, country_code, latitude, longitude
        ) VALUES (
            :place_id, :name, :address, :phone, :website, :email,
            :publicado_en_wp, :wp_post_id, :article_path, :tipo_de_comida,
            :municipality, :city, :postal_code, :country_code, :latitude, :longitude
        )
        """,
        row,
    )
    connection.commit()


@pytest.fixture
def make_place(conn):
    def _make(place_id: str, **overrides):
        insert_place(conn, place_id, **overrides)

    return _make


def add_fake_image(connection: sqlite3.Connection, tmp_path, place_id: str) -> str:
    """Crea un fichero de imagen real en tmp_path y lo registra en
    place_image, para que list_all_places() cuente image_count > 0
    (comprueba os.path.exists ademas de la fila en la tabla)."""
    image_path = tmp_path / f"{place_id}.jpg"
    image_path.write_bytes(b"fake-jpeg-bytes")
    connection.execute(
        "INSERT INTO place_image (place_id, image_path) VALUES (?, ?)",
        (place_id, str(image_path)),
    )
    connection.commit()
    return str(image_path)


def now() -> int:
    return int(time.time())


def clear_seed_locations(connection: sqlite3.Connection) -> None:
    """init_db() precarga 102 ciudades semilla reales (SEED_LOCATIONS); los
    tests de seed_queue necesitan partir de un estado controlado, igual
    que insert_place() parte de una tabla `place` vacía."""
    connection.execute("DELETE FROM seed_location")
    connection.commit()


def insert_seed_location(
    connection: sqlite3.Connection,
    name: str,
    country_code: str = "ES",
    region: str | None = None,
    tier: str = "manual",
    active: int = 1,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO seed_location (country_code, name, region, tier, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (country_code, name, region, tier, active, now()),
    )
    connection.commit()
    return cursor.lastrowid


@pytest.fixture
def make_seed_location(conn):
    clear_seed_locations(conn)

    def _make(name: str, **overrides):
        return insert_seed_location(conn, name, **overrides)

    return _make
