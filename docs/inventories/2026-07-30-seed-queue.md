# Siembra masiva por ciudad (Places API New)

Fecha: 30 de julio de 2026.
Autor: sesión de Claude Code.

## Objetivo

Poder generar automáticamente los 20 mejores negocios de cada capital de
provincia española, repetible al abrir un directorio nuevo (sector
distinto: peluquerías, dentistas...) y exportable a otros países (primero
Estados Unidos, una ciudad principal por estado), sin disparar el coste ni
el rate limit de la API de Google, y con la lista de ciudades semilla
ampliable sin tocar código (ej. añadir Manacor más adelante).

Plan completo (contexto, diseño, alcance) en
`/home/guillem/.claude/plans/witty-twirling-hellman.md`.

## Qué se ha construido

### Reducción real de coste: separar descubrir de enriquecer

Hoy (antes de este cambio) `get_or_create_search()` enriquecía con una
llamada Details (`get_contact_and_location`) **todos** los resultados de
Text Search Legacy, se usaran o no — ese era el multiplicador de coste
real, no la búsqueda en sí. El pipeline de siembra separa los dos pasos:

1. **Descubrimiento** (`app/services/google_places_new.py`): Places API
   **(New)** Text Search (`places:searchText`), con `X-Goog-FieldMask`
   pidiendo solo campos baratos (`id, displayName, formattedAddress,
   rating, userRatingCount, location, businessStatus`). Pagina de verdad
   vía `nextPageToken` (cosa que la Legacy nunca hizo en este proyecto),
   hasta `GOOGLE_SEED_MAX_PAGES` páginas (default 3 → hasta 60
   candidatos), con `GOOGLE_TEXT_SEARCH_PAGE_DELAY_SECONDS` (default 2s)
   entre páginas.
2. **Ranking** (`app/services/place_ranking.py`,
   `select_top_candidates()`): de esos candidatos, top 20 por `rating`
   (desempate por `user_ratings_total`), exigiendo
   `GOOGLE_SEED_MIN_USER_RATINGS` (default 15) reseñas para el corte
   principal — evita que un 5.0 con 1 reseña gane a un 4.6 con 500.
   Si una ciudad pequeña no llega a 20 cualificados, rellena con los
   siguientes mejor valorados. Excluye `CLOSED_PERMANENTLY`.
3. **Enriquecimiento** (sin cambios: `get_contact_and_location`, Details
   Legacy): solo se llama para los 20 ya filtrados, no para los hasta 60
   descubiertos.

### Rate limiting: misma arquitectura de cola que ya existía

`seed_queue.py` replica el patrón exacto de `publication_queue.py`/
`repair_queue.py` (`*_control` con `interval_seconds`/`next_run_at`,
`*_queue` con máquina de estados `pending→processing→completed/failed`,
`_claim_next()` con `BEGIN IMMEDIATE`, worker en hilo daemon). Procesa
**una ciudad a la vez**; ninguna tanda de 52 o 102 ciudades golpea Google
en paralelo.

### Tracking de coste: `google_places_usage`, mismo patrón que `openai_usage`

`app/services/google_places_usage.py::record_google_places_usage()` nunca
lanza excepción (igual que `record_openai_usage`), registra cada llamada
Text Search (New) con `operation, endpoint_version, field_mask, query,
seed_location_id, country_code, directory_search_term, result_count,
status`.

### Generalización a sector: parámetro, no entidad nueva

El término de búsqueda es un parámetro de `POST /seed/start?search_term=`,
con default configurable por env var `DIRECTORY_SEARCH_TERM`. No se
construye la entidad `directory`/`business_type` de Fase 3-4 — eso sigue
pendiente de la capa de repositorios.

### Ciudades semilla, ampliables sin tocar código

Tabla `seed_location(id, country_code, name, region, tier
['capital'|'manual'], active, created_at, UNIQUE(country_code, name,
region))`. **Nota de diseño importante**: la unicidad es sobre las tres
columnas, no solo `(country_code, name)` — EEUU tiene ciudades con el
mismo nombre en estados distintos (Portland en Maine y Oregón; Charleston
en Carolina del Sur y Virginia Occidental), y una restricción más
estrecha habría descartado una de las dos silenciosamente vía `INSERT OR
IGNORE`. Se detectó al construir la lista real, no en abstracto.

Semilla inicial (`app/data/seed_locations.py`, insertada por `init_db()` y
también por la migración Alembic, ambas vía `INSERT OR IGNORE`):
- 52 capitales de provincia españolas (50 + Ceuta y Melilla).
- 50 ciudades de EEUU, la más poblada de cada estado (no la capital
  política — Nueva York no Albany, Los Ángeles no Sacramento),
  verificado contra Wikipedia/Census Bureau
  (https://en.wikipedia.org/wiki/List_of_largest_cities_of_U.S._states_and_territories_by_population,
  consultado el 30 de julio de 2026) en vez de completado de memoria. La
  verificación descartó dos suposiciones incorrectas: Alabama ya no es
  Birmingham sino Huntsville, y la primera versión de la lista española
  omitía A Coruña.

Añadir una ciudad nueva (ej. Manacor): `POST /seed/locations` con
`tier='manual'`. Como la clave de re-encolado en `seed_queue` es el par
`(seed_location_id, search_term)`, relanzar la cola tras añadirla solo la
encola a ella — las demás no se reprocesan para ese término.

### Ficheros nuevos

- `app/data/seed_locations.py` — listas semilla.
- `app/services/google_places_new.py` — cliente Places API (New).
- `app/services/place_ranking.py` — selección top-N.
- `app/services/google_places_usage.py` — tracking de coste.
- `app/services/seed_queue.py` — cola de siembra.
- `app/api/seed.py` — `GET /seed/status`, `POST /seed/start`,
  `POST /seed/pause`, `POST /seed/resume`, `POST /seed/retry-failed`,
  `GET /seed/locations`, `POST /seed/locations`,
  `PATCH /seed/locations/{id}`.
- `alembic/versions/eda8f706cf70_seed_tables_and_google_places_usage.py`
  — 4 tablas nuevas (autogenerate, sin drift) + inserción de la fila de
  control y las 102 ciudades semilla.
- Tests: `test_google_places_new.py`, `test_place_ranking.py`,
  `test_seed_queue.py`, `test_google_places_usage.py` (44 tests nuevos).

### Ficheros modificados

- `app/models/database.py`: esquema de las 4 tablas nuevas en
  `init_db()`; refactor de `get_or_create_search()` para extraer
  `_insert_enriched_results()` (reutilizable) y añadir
  `get_or_create_search_with_candidates()` (variante para candidatos ya
  obtenidos, usada por `seed_queue`); funciones de gestión de
  `seed_location` (`add_seed_location`, `list_seed_locations`,
  `set_seed_location_active`). El endpoint `/places/search` existente no
  cambia de comportamiento.
- `app/models/orm.py`: 4 clases nuevas (`SeedLocation`, `SeedQueueControl`,
  `SeedQueue`, `GooglePlacesUsage`).
- `app/main.py`: registra el router `seed` y arranca su worker junto a
  los otros dos, dentro del mismo `startup()`. El middleware de login ya
  existente cubre `/seed/*` sin cambios.
- `tests/conftest.py`: fixture `make_seed_location` (limpia las 102 filas
  precargadas por `init_db()` para partir de un estado controlado, igual
  que `make_place` parte de una tabla vacía) y monkeypatch de
  `seed_queue.DB_PATH`/`google_places_usage.DB_PATH`.

## Verificación realizada

- **Esquema**: `alembic revision --autogenerate` contra una copia
  migrada al último head detectó exactamente las 4 tablas nuevas, sin
  ruido. `alembic check` tras aplicar: sin drift. `alembic upgrade head`
  + `alembic downgrade -1` sin errores contra una copia de prueba.
  `init_db()` puro (sin Alembic, ejecutado dos veces para probar
  idempotencia) produce el mismo esquema exacto que el camino Alembic
  (comparado columna a columna con `PRAGMA table_info`, `diff` vacío en
  las 4 tablas).
- **Datos semilla**: 52 ES + 50 US = 102 filas únicas tras `init_db()`;
  Portland (Maine/Oregón) y Charleston (Carolina del Sur/Virginia
  Occidental) conviven correctamente gracias a la unicidad de 3 columnas.
- **`python -m compileall`** sobre `app/`, `alembic/` y `tests/`: sin
  errores.
- **`pytest -v`**: 87/87 en verde (43 tests ya existentes sin tocar + 44
  nuevos: `google_places_new` con mocks de `requests.post` —headers,
  paginación, dedupe, delay entre páginas, registro de uso en éxito y en
  error—, `place_ranking` con casos puros del ranking, `seed_queue` con
  la misma batería que las colas existentes, `google_places_usage` con
  inserción/nunca-lanza/resumen agregado).
- **`app.main`**: importado completo (no solo compilado) contra una base
  temporal — confirma que las 8 rutas `/seed/*` quedan registradas y que
  el arranque no rompe con las tablas/imports nuevos.

## Pendiente (a propósito, fuera de esta sesión)

- **No se ha llamado a la API real de Google Places (New) en ningún
  momento** — todo lo anterior está verificado con mocks y contra bases
  de datos de prueba. Antes de lanzar las 102 ciudades hay que seguir el
  plan de verificación manual: 2-3 ciudades de prueba con
  `SEED_AUTOSAVE=false`, revisar `google_places_usage` y unas cuantas
  fichas a mano, y confirmar en Google Cloud Console el SKU/tier de
  facturación real del field mask usado — no se da por buena ninguna
  cifra de coste concreta en el código ni en este documento.
- **Caveat EEUU conocido y no resuelto a propósito**: `province` mapea a
  `administrative_area_level_2`, que en EEUU es el condado, no el estado
  (el estado cae correctamente en `region`). No se renombra la columna
  (afectaría a España sin necesidad; es trabajo de Fase 3 cuando exista
  la capa de repositorios).
- No se ha desplegado nada a producción (`docker compose up -d --build
  backend`) ni se ha ejecutado la migración contra `data/places.db` real
  — todo lo anterior corrió contra copias temporales.
- La lista `USA_MAIN_CITIES` conviene recontrastarla si pasa mucho tiempo
  desde el 30 de julio de 2026, porque el ranking de población de
  ciudades cambia (ya cambió recientemente en Alabama).
