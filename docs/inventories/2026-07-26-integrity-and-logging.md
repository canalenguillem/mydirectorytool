# Restricciones de integridad + logs estructurados

Fecha: 26 de julio de 2026 (sesión continuada el 29 de julio).
Autor: sesión de Claude Code (en ausencia de Codex).

## Objetivo

Cerrar los dos últimos puntos de Fase 1 sin ningún avance
(`docs/roadmap.md`): restricciones de integridad y logs estructurados.

## Restricciones de integridad

Investigación previa contra una copia de `data/places.db`:

| Tabla | Duplicados encontrados |
|---|---:|
| `review` (place_id, author_name, text, time) | 81 grupos, 16 restaurantes afectados |
| `place_image` (place_id, image_path) | 0 |
| `place.place_id` | 0 (el índice único `idx_place_id` ya existía en producción, sin declarar en código — ver `docs/inventories/2026-07-26-sqlalchemy-alembic-baseline.md`) |

Los duplicados de `review` seguían siempre el mismo patrón: la misma
tanda de reseñas insertada dos veces para una ficha, con IDs
consecutivos — compatible con una carrera o una doble llamada al
pipeline en algún momento del historial del proyecto, no con datos
distintos que coincidieran por casualidad.

### Cambio aplicado

`backend/app/models/database.py::init_db()`, mismo patrón que
`_ensure_columns()` (idempotente, se ejecuta en cada arranque):

```python
DELETE FROM review
WHERE id NOT IN (
    SELECT MIN(id) FROM review
    GROUP BY place_id, author_name, text, time
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_place_id ON place(place_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_unique ON review(place_id, author_name, text, time);
CREATE UNIQUE INDEX IF NOT EXISTS idx_place_image_unique ON place_image(place_id, image_path);
```

El `DELETE` solo borra algo la primera vez que corre contra una base con
duplicados históricos; en instalaciones ya limpias (o en cualquier
arranque posterior) no hace nada. `idx_place_id` pasa de existir solo en
producción, sin documentar, a estar declarado en el código — cualquier
instalación nueva (otro directorio futuro) lo tendrá desde el primer
arranque.

También se añadió `backend/alembic/versions/ef082d3b0c89_review_and_place_image_unique_.py`,
una migración nueva sobre la base creada el 26 de julio (no se editó la
migración base ya existente — mala práctica retroactiva), con el mismo
dedup + los dos índices nuevos, y se actualizó `backend/app/models/orm.py`
(`Review`, `PlaceImage`) para reflejarlos.

### Verificación

- Dedup probado con SQL directo contra una copia: 1905 → 1824 filas,
  0 grupos duplicados restantes, índices creados sin error.
- `init_db()` real (no solo el SQL suelto) probado contra una copia:
  mismo resultado.
- Chequeo A (cadena completa de migraciones contra DB vacía): 5 índices
  únicos creados, sin errores.
- Chequeo B (migración nueva aplicada a una copia real, tras `alembic
  stamp` a la revisión anterior): 1905 → 1824, 0 duplicados.
- Chequeo de drift (`alembic revision --autogenerate` tras aplicar):
  al principio señaló los dos índices nuevos como "removed index /
  added unique constraint" — falso positivo cosmético porque se habían
  declarado en `orm.py` como `UniqueConstraint` en vez de `Index(...,
  unique=True)` (SQLite siempre refleja una restricción única como
  índice con nombre). Corregido usando `Index(..., unique=True)`, igual
  que ya hacía `idx_place_id`. Tras el fix, el único ruido restante son
  los 10 falsos positivos ya conocidos de PKs enteras
  (`docs/inventories/2026-07-26-sqlalchemy-alembic-baseline.md`).
- `pytest -v`: 43/43 en verde, sin cambios necesarios en los tests.
- Backup fresco de `data/places.db` tomado inmediatamente antes de
  desplegar (`/home/guillem/backups/dondecomerbien/2026-07-26_pre_integrity_constraints/`),
  porque este cambio borra filas de verdad.
- Desplegado con `docker compose up -d --build backend`. Resultado real
  en producción: 1910 → 1829 filas de `review` (81 borradas, la base
  había crecido 5 filas más desde la última prueba por actividad normal
  de la cola), 0 grupos duplicados, los 5 índices presentes.

## Logs estructurados

39 llamadas a `print()` en 7 ficheros + 2 `traceback.print_exc()` (uno
por cada cola, dentro de `_process_once`) sustituidas por `logging`
estándar de Python. El código ya usaba una convención informal de
prefijos que mapeó casi mecánicamente a niveles:

| Prefijo original | Nivel |
|---|---|
| `[ERROR]` | `logger.error()` |
| `[WARN]` | `logger.warning()` |
| `[OK]` / `[INFO]` | `logger.info()` |
| sin prefijo (restos de depuración) | `logger.debug()` |
| `traceback.print_exc()` en un `except` | `logger.exception()` (incluye el traceback solo) |

Mismo mensaje en cada caso — sustitución mecánica de `print(...)` por
`logger.<nivel>(...)`, sin reescribir texto.

`backend/app/main.py` configura `logging.basicConfig(level=LOG_LEVEL,
format="%(asctime)s %(levelname)s [%(name)s] %(message)s")` al arrancar
(`LOG_LEVEL` configurable por variable de entorno, default `INFO`,
mismo patrón que `CORS_ORIGINS`/`DATA_DIR`). `docker logs
ai_maps-backend-1` sigue siendo el mismo canal de siempre — solo cambia
el formato de cada línea.

Ficheros tocados: `main.py`, `wordpress.py` (23 sitios), `blog.py` (7),
`database.py` (5), `featured_image.py`, `openai_usage.py`,
`place_images.py`, `export_reviews.py`, `publication_queue.py`,
`repair_queue.py`.

### Verificación

- `grep -rn "print(" backend/app` tras el cambio: sin resultados en
  toda la app.
- `python -m py_compile` sobre los 10 ficheros: sin errores.
- Probado el logger configurado dentro del contenedor ya desplegado
  (`logging.getLogger("app.services.wordpress").info(...)`): confirma
  el formato `timestamp NIVEL [módulo] mensaje` funcionando de verdad,
  no solo en teoría.

## Pendiente

- Los otros dos puntos de Fase 1 siguen sin tocar: homogeneizar
  respuestas/códigos HTTP y timeouts/reintentos sistemáticos en todas
  las integraciones.
- No se investigó la causa raíz de por qué esas 16 fichas tuvieron
  reseñas duplicadas (probablemente una carrera histórica ya resuelta
  por otros cambios de esta sesión) — con la restricción única puesta,
  no puede volver a pasar, pero no se confirmó el porqué original.
