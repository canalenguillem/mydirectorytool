import sqlite3
import hashlib
import json
import logging
from app.data.seed_locations import seed_locations_for
from app.services.google_places import buscar_lugares
import os
import time

logger = logging.getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "places.db")

LOCATION_COLUMNS = {
    "country": "TEXT",
    "country_code": "TEXT",
    "region": "TEXT",
    "province": "TEXT",
    "municipality": "TEXT",
    "city": "TEXT",
    "district": "TEXT",
    "latitude": "REAL",
    "longitude": "REAL",
    "email": "TEXT",
    "email_source": "TEXT",
    "business_status": "TEXT",
}


def _ensure_columns(cursor, table: str, columns: dict[str, str]):
    existing = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})")}
    for name, column_type in columns.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Taula de cerques
    c.execute("""
    CREATE TABLE IF NOT EXISTS search (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT UNIQUE,
        query_hash TEXT UNIQUE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS search_result (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_id INTEGER NOT NULL,
        name TEXT,
        address TEXT,
        place_id TEXT NOT NULL,
        rating REAL,
        postal_code TEXT,
        phone TEXT,
        website TEXT,
        country TEXT,
        country_code TEXT,
        region TEXT,
        province TEXT,
        municipality TEXT,
        city TEXT,
        district TEXT,
        latitude REAL,
        longitude REAL,
        email TEXT,
        email_source TEXT,
        business_status TEXT,
        UNIQUE(search_id, place_id),
        FOREIGN KEY(search_id) REFERENCES search(id)
    )
    """)

    # Taula de llocs trobats
    c.execute("""
    CREATE TABLE IF NOT EXISTS place (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_id INTEGER,
        name TEXT,
        address TEXT,
        place_id TEXT,
        rating REAL,
        postal_code TEXT,
        phone TEXT,
        website TEXT,
        article_path TEXT,
        publicado_en_wp INTEGER DEFAULT 0,
        wp_post_id INTEGER,
        tipo_de_comida TEXT,
        country TEXT,
        country_code TEXT,
        region TEXT,
        province TEXT,
        municipality TEXT,
        city TEXT,
        district TEXT,
        latitude REAL,
        longitude REAL,
        email TEXT,
        email_source TEXT,
        business_status TEXT,
        FOREIGN KEY(search_id) REFERENCES search(id)
    )
    """)

    _ensure_columns(c, "search_result", LOCATION_COLUMNS)
    _ensure_columns(c, "place", LOCATION_COLUMNS)

    # Ressenyes individuals
    c.execute("""
    CREATE TABLE IF NOT EXISTS review (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT,
        author_name TEXT,
        rating REAL,
        text TEXT,
        time INTEGER
    )
    """)

    # Text complet de les ressenyes (concatenades)
    c.execute("""
    CREATE TABLE IF NOT EXISTS review_text (
        place_id TEXT PRIMARY KEY,
        name TEXT,
        address TEXT,
        locality TEXT,
        phone TEXT,
        full_text TEXT
    )
    """)

    # Articles generats (per idioma)
    c.execute("""
    CREATE TABLE IF NOT EXISTS blog_article (
        place_id TEXT,
        lang TEXT,
        path TEXT,
        locality TEXT,
        PRIMARY KEY (place_id, lang)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS place_image (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT,
        image_path TEXT,
        FOREIGN KEY(place_id) REFERENCES place(place_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS place_featured_image (
    place_id TEXT PRIMARY KEY,
    image_path TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS publication_queue_control (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        active INTEGER NOT NULL DEFAULT 0,
        interval_seconds INTEGER NOT NULL DEFAULT 300,
        next_run_at INTEGER,
        updated_at INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS publication_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        last_error TEXT,
        created_at INTEGER NOT NULL,
        started_at INTEGER,
        finished_at INTEGER,
        FOREIGN KEY(place_id) REFERENCES place(place_id)
    )
    """)

    c.execute("""
        INSERT OR IGNORE INTO publication_queue_control
            (id, active, interval_seconds, next_run_at, updated_at)
        VALUES (1, 0, 300, NULL, strftime('%s', 'now'))
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS repair_queue_control (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        active INTEGER NOT NULL DEFAULT 0,
        interval_seconds INTEGER NOT NULL DEFAULT 300,
        next_run_at INTEGER,
        updated_at INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS repair_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        last_error TEXT,
        created_at INTEGER NOT NULL,
        started_at INTEGER,
        finished_at INTEGER,
        FOREIGN KEY(place_id) REFERENCES place(place_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS openai_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at INTEGER NOT NULL,
        operation TEXT NOT NULL,
        model TEXT NOT NULL,
        place_id TEXT,
        prompt_tokens INTEGER NOT NULL DEFAULT 0,
        completion_tokens INTEGER NOT NULL DEFAULT 0,
        total_tokens INTEGER NOT NULL DEFAULT 0,
        cached_tokens INTEGER NOT NULL DEFAULT 0,
        response_id TEXT
    )
    """)
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_openai_usage_created_at
    ON openai_usage(created_at)
    """)
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_openai_usage_place_id
    ON openai_usage(place_id)
    """)

    c.execute("""
        INSERT OR IGNORE INTO repair_queue_control
            (id, active, interval_seconds, next_run_at, updated_at)
        VALUES (1, 0, 300, NULL, strftime('%s', 'now'))
    """)

    # Siembra masiva por ciudad (30 de julio de 2026). Ver
    # docs/inventories/2026-07-30-seed-queue.md.
    c.execute("""
    CREATE TABLE IF NOT EXISTS seed_location (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_code TEXT NOT NULL,
        name TEXT NOT NULL,
        region TEXT,
        tier TEXT NOT NULL DEFAULT 'manual' CHECK (tier IN ('capital', 'manual')),
        active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL,
        UNIQUE(country_code, name, region)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS seed_queue_control (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        active INTEGER NOT NULL DEFAULT 0,
        interval_seconds INTEGER NOT NULL DEFAULT 300,
        next_run_at INTEGER,
        updated_at INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS seed_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seed_location_id INTEGER NOT NULL,
        search_term TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        last_error TEXT,
        places_found INTEGER,
        places_saved INTEGER,
        created_at INTEGER NOT NULL,
        started_at INTEGER,
        finished_at INTEGER,
        UNIQUE(seed_location_id, search_term),
        FOREIGN KEY(seed_location_id) REFERENCES seed_location(id)
    )
    """)

    c.execute("""
        INSERT OR IGNORE INTO seed_queue_control
            (id, active, interval_seconds, next_run_at, updated_at)
        VALUES (1, 0, 300, NULL, strftime('%s', 'now'))
    """)

    # Cada instalación se centra en el/los país(es) que le tocan -- no en
    # todos los que este código conoce. Por defecto solo España; para un
    # directorio en otro país (o varios) se configura DIRECTORY_COUNTRY_CODE
    # (ej. "US" o "ES,US") antes del primer arranque.
    directory_countries = [
        code.strip().upper()
        for code in os.environ.get("DIRECTORY_COUNTRY_CODE", "ES").split(",")
        if code.strip()
    ]
    c.executemany(
        """
        INSERT OR IGNORE INTO seed_location
            (country_code, name, region, tier, active, created_at)
        VALUES (?, ?, ?, ?, 1, strftime('%s', 'now'))
        """,
        seed_locations_for(directory_countries),
    )

    c.execute("""
    CREATE TABLE IF NOT EXISTS google_places_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at INTEGER NOT NULL,
        operation TEXT NOT NULL,
        endpoint_version TEXT NOT NULL,
        field_mask TEXT,
        query TEXT,
        seed_location_id INTEGER,
        country_code TEXT,
        directory_search_term TEXT,
        result_count INTEGER,
        status TEXT,
        place_id TEXT,
        FOREIGN KEY(seed_location_id) REFERENCES seed_location(id)
    )
    """)
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_google_places_usage_created_at
    ON google_places_usage(created_at)
    """)
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_google_places_usage_seed_location_id
    ON google_places_usage(seed_location_id)
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS basket (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS basket_place (
        basket_id INTEGER NOT NULL,
        place_id TEXT NOT NULL,
        added_at INTEGER NOT NULL,
        PRIMARY KEY (basket_id, place_id),
        FOREIGN KEY(basket_id) REFERENCES basket(id)
    )
    """)

    # Restricciones de integridad (26 de julio de 2026). El DELETE es
    # idempotente: solo borra algo la primera vez que se ejecuta contra
    # una base con duplicados históricos; en instalaciones ya limpias no
    # hace nada. Ver docs/inventories/2026-07-26-integrity-and-logging.md.
    c.execute("""
        DELETE FROM review
        WHERE id NOT IN (
            SELECT MIN(id) FROM review
            GROUP BY place_id, author_name, text, time
        )
    """)
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_place_id ON place(place_id)")
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_review_unique "
        "ON review(place_id, author_name, text, time)"
    )
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_place_image_unique "
        "ON place_image(place_id, image_path)"
    )

    conn.commit()
    conn.close()


def hash_query(query):
    return hashlib.sha256(query.lower().encode()).hexdigest()

def get_or_create_search(query):
    logger.debug("get_or_create_search")
    query_hash = hash_query(query)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Comprova si la cerca ja existeix
    c.execute("SELECT id FROM search WHERE query_hash = ?", (query_hash,))
    row = c.fetchone()
    if row:
        logger.debug(f"dins if row {row[0]}")
        search_id = row[0]
        c.execute("""
            SELECT name, address, place_id, rating, postal_code, phone, website,
                   country, country_code, region, province, municipality, city,
                   district, latitude, longitude, email, email_source, business_status
            FROM search_result
            WHERE search_id = ?
        """, (search_id,))
        places = [
            dict(zip(["name", "address", "place_id", "rating", "postal_code", "phone", "website", "country", "country_code", "region", "province", "municipality", "city", "district", "latitude", "longitude", "email", "email_source", "business_status"], r))
            for r in c.fetchall()
        ]
        # Compatibilidad con búsquedas creadas antes de separar resultados y
        # lugares guardados. Se eliminará cuando todas hayan sido migradas.
        if not places:
            c.execute("""
                SELECT name, address, place_id, rating, postal_code, phone, website,
                       country, country_code, region, province, municipality, city,
                       district, latitude, longitude, email, email_source, business_status
                FROM place WHERE search_id = ?
            """, (search_id,))
            places = [
                dict(zip(["name", "address", "place_id", "rating", "postal_code", "phone", "website", "country", "country_code", "region", "province", "municipality", "city", "district", "latitude", "longitude", "email", "email_source", "business_status"], r))
                for r in c.fetchall()
            ]
        conn.close()
        return places
    else:
        # Fetch des de l'API
        logger.debug("dins buscar lugares")
        lugares = buscar_lugares(query)
        c.execute("INSERT INTO search (query, query_hash) VALUES (?, ?)", (query, query_hash))
        search_id = c.lastrowid
        _insert_enriched_results(c, search_id, lugares)
        conn.commit()
        conn.close()
        return get_or_create_search(query)


def _insert_enriched_results(cursor, search_id: int, lugares: list[dict]) -> None:
    """Bucle de enriquecimiento (Details) + INSERT en search_result.
    Extraído de get_or_create_search para poder reutilizarlo desde el
    pipeline de siembra (seed_queue.py) con candidatos ya filtrados
    (top-N), en vez de recibir siempre "hasta 20, todos" de buscar_lugares."""
    from app.services.google_places import get_contact_and_location

    details_delay = float(os.environ.get("GOOGLE_DETAILS_DELAY_SECONDS", "0.25"))

    for lugar in lugares:
        try:
            details = get_contact_and_location(lugar["place_id"])
        except Exception as exc:
            # Un fallo puntual o un límite temporal no debe perder todos
            # los resultados de la búsqueda. Conservamos los datos básicos
            # y las coordenadas que ya devuelve Text Search.
            location = lugar.get("geometry", {}).get("location", {})
            details = {
                "latitude": location.get("lat"),
                "longitude": location.get("lng"),
            }
            logger.warning(f"Sin detalles para {lugar['place_id']}: {exc}")

        cursor.execute("""
            INSERT OR IGNORE INTO search_result (
                search_id, name, address, place_id, rating,
                postal_code, phone, website, country, country_code,
                region, province, municipality, city, district,
                latitude, longitude, email, email_source, business_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            search_id,
            lugar["name"],
            lugar.get("formatted_address", ""),
            lugar["place_id"],
            lugar.get("rating", 0),
            details.get("postal_code", ""),
            details.get("phone", ""),
            details.get("website", ""),
            details.get("country", ""),
            details.get("country_code", ""),
            details.get("region", ""),
            details.get("province", ""),
            details.get("municipality", ""),
            details.get("city", ""),
            details.get("district", ""),
            details.get("latitude"),
            details.get("longitude"),
            details.get("email", ""),
            details.get("email_source", ""),
            details.get("business_status", ""),
        ))
        if details_delay > 0:
            time.sleep(details_delay)


def get_or_create_search_with_candidates(query: str, lugares: list[dict]) -> list[dict]:
    """Igual que get_or_create_search, pero recibe candidatos ya obtenidos
    (Places API New + ranking top-N) en vez de llamar a buscar_lugares()
    (Legacy). Usado por el pipeline de siembra (seed_queue.py). Si la
    query ya existe en caché, se limita a devolverla -- no reinserta."""
    query_hash = hash_query(query)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM search WHERE query_hash = ?", (query_hash,))
    if c.fetchone():
        conn.close()
        return get_or_create_search(query)

    c.execute("INSERT INTO search (query, query_hash) VALUES (?, ?)", (query, query_hash))
    search_id = c.lastrowid
    _insert_enriched_results(c, search_id, lugares)
    conn.commit()
    conn.close()
    return get_or_create_search(query)


def list_seed_searches(search_term: str | None = None) -> list[dict]:
    """Lista las búsquedas generadas por la cola de siembra (seed_queue.py),
    con cuántos candidatos descubrió cada una y cuántos ya están guardados
    en `place`. La query sembrada siempre tiene la forma "<search_term> en
    <ciudad>" (ver seed_queue._run_pipeline), así que se reconoce por LIKE
    'restaurantes en %' salvo que se pida otro search_term explícito."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    pattern = f"{search_term} en %" if search_term else "% en %"
    rows = conn.execute(
        """
        SELECT
            s.id AS search_id,
            s.query,
            COUNT(sr.id) AS total,
            SUM(CASE WHEN p.place_id IS NOT NULL THEN 1 ELSE 0 END) AS saved
        FROM search s
        JOIN search_result sr ON sr.search_id = s.id
        LEFT JOIN place p ON p.place_id = sr.place_id
        WHERE s.query LIKE ?
        GROUP BY s.id, s.query
        ORDER BY s.query
        """,
        (pattern,),
    ).fetchall()
    conn.close()
    return [
        {
            "search_id": row["search_id"],
            "query": row["query"],
            "total": row["total"],
            "saved": row["saved"] or 0,
            "pending": row["total"] - (row["saved"] or 0),
        }
        for row in rows
    ]


def get_search_candidates(search_id: int) -> list[dict]:
    """Candidatos de una búsqueda concreta (por id), con un flag `saved`
    indicando si ya están en `place`. Reutilizado por el panel para revisar
    y guardar uno a uno lo que descubrió la siembra."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            sr.name, sr.address, sr.place_id, sr.rating, sr.postal_code,
            sr.phone, sr.website, sr.country, sr.country_code, sr.region,
            sr.province, sr.municipality, sr.city, sr.district,
            sr.latitude, sr.longitude, sr.email, sr.email_source,
            sr.business_status,
            CASE WHEN p.place_id IS NOT NULL THEN 1 ELSE 0 END AS saved
        FROM search_result sr
        LEFT JOIN place p ON p.place_id = sr.place_id
        WHERE sr.search_id = ?
        ORDER BY sr.rating DESC
        """,
        (search_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_search_result(place_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT search_id, name, address, place_id, rating, postal_code, phone, website,
               country, country_code, region, province, municipality, city,
               district, latitude, longitude, email, email_source, business_status
        FROM search_result
        WHERE place_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (place_id,)).fetchone()
    if not row:
        conn.close()
        return None

    existing = conn.execute(
        "SELECT 1 FROM place WHERE place_id = ? LIMIT 1", (place_id,)
    ).fetchone()
    if not existing:
        conn.execute("""
            INSERT INTO place (
                search_id, name, address, place_id, rating,
                postal_code, phone, website, country, country_code,
                region, province, municipality, city, district,
                latitude, longitude, email, email_source, business_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(row))
        conn.commit()
    conn.close()
    return dict(row)


def enrich_place_details(place_id: str) -> dict:
    """Fill missing contact and location fields for an already saved place."""
    from app.services.google_places import get_contact_and_location

    details = get_contact_and_location(place_id)
    text_fields = (
        "postal_code", "phone", "website", "country", "country_code",
        "region", "province", "municipality", "city", "district",
        "email", "email_source", "business_status",
    )
    numeric_fields = ("latitude", "longitude")

    conn = sqlite3.connect(DB_PATH)
    try:
        assignments = [
            f"{field} = CASE WHEN COALESCE({field}, '') = '' THEN ? ELSE {field} END"
            for field in text_fields
        ]
        assignments.extend(
            f"{field} = COALESCE({field}, ?)" for field in numeric_fields
        )
        values = [details.get(field, "") for field in text_fields]
        values.extend(details.get(field) for field in numeric_fields)
        conn.execute(
            f"UPDATE place SET {', '.join(assignments)} WHERE place_id = ?",
            (*values, place_id),
        )
        conn.commit()
    finally:
        conn.close()

    return details

def list_all_places():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT name, address, place_id, rating, publicado_en_wp, phone, website,
               wp_post_id, article_path, postal_code, country, country_code,
               region, province, municipality, city, district, latitude,
               longitude, email, email_source, business_status, tipo_de_comida,
               (
                   SELECT COUNT(*)
                   FROM place_image
                   WHERE place_image.place_id = place.place_id
               ) AS image_count
        FROM place
    """)
    keys = [
        "name", "address", "place_id", "rating", "publicado_en_wp", "phone",
        "website", "wp_post_id", "article_path", "postal_code", "country",
        "country_code", "region", "province", "municipality", "city",
        "district", "latitude", "longitude", "email", "email_source",
        "business_status", "tipo_de_comida", "image_count",
    ]
    places = [dict(zip(keys, row)) for row in c.fetchall()]
    image_paths = {}
    for place_id, image_path in c.execute(
        "SELECT place_id, image_path FROM place_image"
    ).fetchall():
        image_paths.setdefault(place_id, []).append(image_path)
    conn.close()

    for place in places:
        place["image_count"] = sum(
            1
            for image_path in image_paths.get(place["place_id"], [])
            if image_path and os.path.exists(image_path)
        )
        flags = []
        if not any(
            str(place.get(field) or "").strip()
            for field in ("phone", "website", "email")
        ):
            flags.append("contact")
        if (
            not any(
                str(place.get(field) or "").strip()
                for field in ("municipality", "city")
            )
            or place.get("latitude") is None
            or place.get("longitude") is None
            or not str(place.get("postal_code") or "").strip()
            or not str(place.get("country_code") or "").strip()
        ):
            flags.append("location")
        if not place.get("image_count"):
            flags.append("images")
        if not str(place.get("tipo_de_comida") or "").strip():
            flags.append("food_type")
        if (
            place.get("publicado_en_wp")
            and place.get("wp_post_id")
            and not str(place.get("article_path") or "").strip()
        ):
            flags.append("wordpress_link")

        place["incomplete_fields"] = flags
        place["is_incomplete"] = bool(flags)

    return places

def save_reviews_for_place(place_id, reviews):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for r in reviews:
        c.execute("""
        INSERT INTO review (place_id, author_name, rating, text, time)
        VALUES (?, ?, ?, ?, ?)
        """, (
            place_id,
            r.get("author_name", ""),
            r.get("rating", 0),
            r.get("text", ""),
            r.get("time", 0)
        ))
    conn.commit()
    conn.close()


def get_or_create_concatenated_reviews(place_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Comprova si ja tenim el text concatenat
    c.execute("SELECT full_text FROM review_text WHERE place_id = ?", (place_id,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]

    # Importem el detall del lloc
    from app.services.google_places import get_place_details, get_reviews
    details = get_place_details(place_id)

    # Obtenim info del lloc
    name = details.get("name", "")
    address = details.get("formatted_address", "")
    phone = details.get("international_phone_number", "")
    locality = extract_locality_from_address(address)  # ho definim abaix

    # Ressenyes: si ja no les tenim a la base de dades, les guardam
    c.execute("SELECT text FROM review WHERE place_id = ?", (place_id,))
    reviews = [r[0] for r in c.fetchall()]

    if not reviews:
        new_reviews = details.get("reviews", [])
        from app.models.database import save_reviews_for_place
        save_reviews_for_place(place_id, new_reviews)
        reviews = [r["text"] for r in new_reviews]

    full_text = "\n".join(reviews)

    # Inserim el registre complet
    c.execute("""
        INSERT INTO review_text (place_id, name, address, locality, phone, full_text)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (place_id, name, address, locality, phone, full_text))
    conn.commit()
    conn.close()
    return full_text

def extract_locality_from_address(address):
    if "," in address:
        parts = address.split(",")
        if len(parts) >= 2:
            return parts[-2].strip()
    return ""

def get_or_create_review_info(place_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Comprova si ja tenim la info guardada
    c.execute("""
        SELECT name, address, locality, phone, full_text
        FROM review_text WHERE place_id = ?
    """, (place_id,))
    row = c.fetchone()
    if row:
        c.execute("""
            SELECT website, city, municipality, email
            FROM place WHERE place_id = ?
        """, (place_id,))
        place_row = c.fetchone()
        website = place_row[0] if place_row and place_row[0] else ""
        locality = (
            (place_row[1] or place_row[2])
            if place_row and (place_row[1] or place_row[2])
            else row[2]
        )
        conn.close()
        return {
            "place_id": place_id,
            "name": row[0],
            "address": row[1],
            "locality": locality,
            "phone": row[3],
            "text": row[4],
            "website": website,
            "email": place_row[3] if place_row and place_row[3] else "",
        }

    # Si no la tenim, la generam (es crida la mateixa funció que abans)
    text = get_or_create_concatenated_reviews(place_id)

    # Un cop generada, la tornam a cercar i retornar
    return get_or_create_review_info(place_id)


import os
import re

ARTICLES_DIR = os.path.join(DATA_DIR, "articles")
os.makedirs(ARTICLES_DIR, exist_ok=True)

def get_or_create_article(info: dict, lang: str, generator_func):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT path FROM blog_article WHERE place_id = ? AND lang = ?", (info["place_id"], lang))
    row = c.fetchone()

    if row and os.path.exists(row[0]):
        path = row[0]
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # Algunas filas antiguas apuntan a la estructura previa (`articles/`).
    # Si el archivo ya no existe, eliminamos solo el registro huérfano para
    # poder regenerarlo bajo DATA_DIR/articles.
    if row:
        c.execute(
            "DELETE FROM blog_article WHERE place_id = ? AND lang = ?",
            (info["place_id"], lang),
        )
        conn.commit()

    # Si no existeix, generar i desar
    article = generator_func(info, lang)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", info['name'])[:40]  # Nom netejat, màxim 40 caràcters
    filename = f"descripcion_{safe_name}_{info['place_id']}_{lang}.md"
    path = os.path.join(ARTICLES_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(article)

    # Registrar a la BBDD
    c.execute("""
        INSERT INTO blog_article (place_id, lang, path, locality)
        VALUES (?, ?, ?, ?)
    """, (info["place_id"], lang, path, info["locality"]))
    conn.commit()
    conn.close()
    return article

def get_all_articles():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT place_id, locality, lang, path FROM blog_article
    """)
    articles = [dict(zip(["place_id", "locality", "lang", "path"], row)) for row in c.fetchall()]
    conn.close()
    return articles
def delete_article(place_id: str, lang: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Comprova si existeix
    c.execute("SELECT path FROM blog_article WHERE place_id = ? AND lang = ?", (place_id, lang))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "No s'ha trobat cap article amb aquests valors."

    path = row[0]

    # Esborra el fitxer si existeix
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        return False, f"Error esborrant el fitxer: {e}"

    # Esborra de la base de dades
    c.execute("DELETE FROM blog_article WHERE place_id = ? AND lang = ?", (place_id, lang))
    conn.commit()
    conn.close()
    return True, "Article eliminat correctament."


import os
import json

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

def exportar_reviews_a_json():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT DISTINCT place_id FROM review")
    place_ids = [row[0] for row in c.fetchall()]

    fitxers_exportats = []

    for pid in place_ids:
        # Info del lloc
        c.execute("SELECT name, address, locality, phone FROM review_text WHERE place_id = ?", (pid,))
        row = c.fetchone()
        if not row:
            continue
        name, address, locality, phone = row

        # Ressenyes
        c.execute("SELECT author_name, rating, text, time FROM review WHERE place_id = ?", (pid,))
        reviews = [
            {"author": r[0], "rating": r[1], "text": r[2], "time": r[3]}
            for r in c.fetchall()
        ]

        data = {
            "place_id": pid,
            "name": name,
            "address": address,
            "locality": locality,
            "phone": phone,
            "reviews": reviews
        }

        filename = f"{EXPORT_DIR}/{locality}_{name[:20].replace(' ', '_')}_{pid[:6]}.json".replace("/", "_")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        fitxers_exportats.append(filename)

    conn.close()
    return len(fitxers_exportats), fitxers_exportats


def get_places_by_postal_code(postal_code: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT name, address, place_id, rating, postal_code
        FROM place
        WHERE postal_code = ?
    """, (postal_code,))
    rows = c.fetchall()
    conn.close()
    return [dict(zip(["name", "address", "place_id", "rating", "postal_code"], row)) for row in rows]

def marcar_publicado(place_id, wp_post_id, wp_url=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE place SET publicado_en_wp = 1, wp_post_id = ?, article_path = ? WHERE place_id = ?", (wp_post_id, wp_url, place_id))
    conn.commit()
    conn.close()


def set_place_food_type(place_id: str, food_type: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE place SET tipo_de_comida = ? WHERE place_id = ?",
            (food_type, place_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_places_by_ids(place_ids: list[str]) -> list[dict]:
    """Fichas concretas por place_id, en el mismo orden pedido -- usado
    para reunir la "cesta" de un artículo de resumen (roundup)."""
    if not place_ids:
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in place_ids)
    rows = conn.execute(
        f"""
        SELECT place_id, name, city, municipality, rating, publicado_en_wp, wp_post_id
        FROM place
        WHERE place_id IN ({placeholders})
        """,
        place_ids,
    ).fetchall()
    conn.close()
    by_id = {row["place_id"]: dict(row) for row in rows}
    return [by_id[pid] for pid in place_ids if pid in by_id]


def create_basket(name: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO basket (name, created_at) VALUES (?, strftime('%s', 'now'))",
        (name,),
    )
    conn.commit()
    basket_id = cur.lastrowid
    conn.close()
    return {"id": basket_id, "name": name}


def list_baskets() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT b.id, b.name, b.created_at, COUNT(bp.place_id) AS place_count
        FROM basket b
        LEFT JOIN basket_place bp ON bp.basket_id = b.id
        GROUP BY b.id
        ORDER BY b.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_basket(basket_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    basket = conn.execute(
        "SELECT id, name, created_at FROM basket WHERE id = ?", (basket_id,)
    ).fetchone()
    if not basket:
        conn.close()
        return None
    places = conn.execute("""
        SELECT p.place_id, p.name, p.city, p.municipality, p.rating,
               p.publicado_en_wp, p.wp_post_id
        FROM basket_place bp
        JOIN place p ON p.place_id = bp.place_id
        WHERE bp.basket_id = ?
        ORDER BY bp.added_at
    """, (basket_id,)).fetchall()
    conn.close()
    result = dict(basket)
    result["places"] = [dict(row) for row in places]
    return result


def add_place_to_basket(basket_id: int, place_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO basket_place (basket_id, place_id, added_at) "
        "VALUES (?, ?, strftime('%s', 'now'))",
        (basket_id, place_id),
    )
    conn.commit()
    conn.close()


def remove_place_from_basket(basket_id: int, place_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "DELETE FROM basket_place WHERE basket_id = ? AND place_id = ?",
        (basket_id, place_id),
    )
    conn.commit()
    conn.close()


def delete_basket(basket_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM basket_place WHERE basket_id = ?", (basket_id,))
    conn.execute("DELETE FROM basket WHERE id = ?", (basket_id,))
    conn.commit()
    conn.close()


def get_article_data(place_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT 
            p.name, p.address, p.place_id, p.rating, p.postal_code,
            p.phone, p.website, p.tipo_de_comida,
            p.publicado_en_wp, p.wp_post_id, p.article_path,
            p.email, p.country, p.country_code, p.region, p.province,
            p.municipality, p.city, p.district, p.latitude, p.longitude,
            b.path
        FROM place p
        LEFT JOIN blog_article b ON p.place_id = b.place_id
        WHERE p.place_id = ?
    """, (place_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    keys = [
        "name", "address", "place_id", "rating", "postal_code",
        "phone", "website", "tipo_de_comida", "publicado_en_wp",
        "wp_post_id", "wp_url", "email", "country", "country_code",
        "region", "province", "municipality", "city", "district",
        "latitude", "longitude", "article_path"
    ]
    data = dict(zip(keys, row))

    # Llegeix el fitxer .md amb l'article
    try:
        with open(data["article_path"], "r", encoding="utf-8") as f:
            data["content"] = f.read()
    except Exception as e:
        logger.error(f"No s'ha trobat el fitxer .md: {data['article_path']}")
        data["content"] = ""

    # Títol per defecte
    match = re.search(r'^# (.+)', data["content"], re.MULTILINE)
    if match:
        data["title"] = match.group(1).strip()
    else:
        data["title"] = data["name"]

    # Just abans d'enviar el contingut a WordPress
    if data["content"].startswith("# "):
        primera_linia, *rest = data["content"].split("\n", 1)
        data["content"] = rest[0] if rest else ""
    return data


def get_all_images_for_place(place_id: str) -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT image_path FROM place_image WHERE place_id = ?", (place_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def add_seed_location(
    country_code: str, name: str, region: str | None = None, tier: str = "manual"
) -> dict:
    """Añade una ciudad semilla (ej. Manacor) sin tocar código -- ver
    seed_queue.py. Idempotente: si ya existe (country_code, name, region),
    no la duplica."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        INSERT OR IGNORE INTO seed_location
            (country_code, name, region, tier, active, created_at)
        VALUES (?, ?, ?, ?, 1, strftime('%s', 'now'))
        """,
        (country_code, name, region, tier),
    )
    conn.commit()
    row = conn.execute(
        """
        SELECT id, country_code, name, region, tier, active, created_at
        FROM seed_location
        WHERE country_code = ? AND name = ? AND region IS ?
        """,
        (country_code, name, region),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def list_seed_locations(country_code: str | None = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    sql = "SELECT id, country_code, name, region, tier, active, created_at FROM seed_location"
    params: tuple = ()
    if country_code:
        sql += " WHERE country_code = ?"
        params = (country_code,)
    sql += " ORDER BY country_code, name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_seed_location_active(location_id: int, active: bool) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "UPDATE seed_location SET active = ? WHERE id = ?",
        (1 if active else 0, location_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, country_code, name, region, tier, active, created_at "
        "FROM seed_location WHERE id = ?",
        (location_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}
