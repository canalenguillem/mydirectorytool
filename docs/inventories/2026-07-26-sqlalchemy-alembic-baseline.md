# Modelos SQLAlchemy + migración base con Alembic

Fecha: 26 de julio de 2026.
Autor: sesión de Claude Code (en ausencia de Codex).

## Objetivo

Primer paso del plan de migración a PostgreSQL
(`docs/postgresql-migration-plan.md` §6, pasos 1 y 5): introducir modelos
SQLAlchemy y una migración base con Alembic que representen el esquema actual
de SQLite, **sin tocar el motor ni reescribir ningún caso de uso existente**.
La app sigue funcionando exactamente igual que antes; esto es infraestructura
paralela e inerte.

## Qué se añadió

| Fichero | Contenido |
| --- | --- |
| `backend/app/models/orm.py` | 13 modelos SQLAlchemy 2.0 (`DeclarativeBase`/`Mapped`/`mapped_column`), uno por tabla. No se importa desde `app.main` ni ningún router/servicio. |
| `backend/alembic.ini` | Config de Alembic. `sqlalchemy.url` deliberadamente sin fijar — se calcula en `env.py`. |
| `backend/alembic/env.py` | Calcula la URL igual que `database.py` (`DATA_DIR` env var, mismo fallback a `"."`), para que funcione igual en local y en el contenedor sin config nueva. `render_as_batch=True` activado desde ya. |
| `backend/alembic/versions/36597ddfe5ad_baseline_schema.py` | Migración base, escrita a mano (`op.create_table`/`op.create_index`), no generada por autogenerate. |
| `backend/requirements.txt` | `sqlalchemy>=2.0.35`, `alembic>=1.13.2` añadidos. |

**`init_db()` / `_ensure_columns()` no se han tocado.** Siguen siendo, hoy,
lo único que crea/evoluciona el esquema en producción. No se ha ejecutado
`alembic upgrade head` ni `alembic stamp head` contra `data/places.db` real
— decisión deliberada, no un olvido: ningún código de la app depende
todavía de Alembic.

**Los 10 ficheros que hoy usan `sqlite3.connect()` directamente no cambian**
(`database.py`, `publication_queue.py`, `repair_queue.py`, `openai_usage.py`,
`place_deletion.py`, `wordpress.py`, `article_titles.py`, `featured_image.py`,
`api/places.py`, `export/export_reviews.py`) — confirmado con
`git diff --stat` sobre los 10, sin salida.

## Por qué migración escrita a mano y no autogenerate

Es una migración de creación (DB vacía → esquema completo), sin ningún
`ALTER TABLE` de por medio, así que la limitación de SQLite con `ALTER TABLE`
(la razón habitual para preferir autogenerate + batch mode) no aplica aquí.
Escribirla a mano la hace revisable línea a línea contra `init_db()`, sin
depender de que los modelos ya fueran perfectos de entrada.

Autogenerate sí se usó, pero como herramienta de **verificación**, no como
fuente de la migración (ver Chequeo B).

## Hallazgo: drift no documentado en producción

Al comparar contra una copia de `data/places.db` real apareció algo que no
estaba en `init_db()`, en ningún otro fichero del repo ni en el historial de
git (`git log --all -S "idx_place_id"` sin resultados):

```sql
CREATE UNIQUE INDEX idx_place_id ON place(place_id);
```

Es decir: **`place.place_id` sí tiene un índice único en producción hoy**,
aunque `docs/postgresql-migration-plan.md` §7 lo lista como limpieza
pendiente ("Resolver duplicados de place_id"). Se añadió en algún momento
directamente contra la base real, sin dejar rastro documentado. Se ha
modelado el índice único en `orm.py` y en la migración para reflejar la
realidad, pero la columna sigue sin `NOT NULL` (tampoco lo es hoy). No se ha
investigado más a fondo el origen de este índice — queda para quien retome
este trabajo confirmar si fue intencional y si los datos actuales cumplen la
unicidad de verdad.

## Verificación realizada (solo sobre copias, nunca sobre `data/places.db` ni el contenedor)

**Chequeo A — equivalencia estructural:**
```bash
DATA_DIR=$(mktemp -d) alembic upgrade head
# comparar sqlite3 .schema resultante contra una copia de data/places.db
```
Resultado: 13 tablas en ambos lados, mismos 3 índices
(`idx_place_id` UNIQUE, `idx_openai_usage_created_at`,
`idx_openai_usage_place_id`).

**Chequeo B — autogenerate diff contra datos reales (el más fuerte):**
```bash
cp data/places.db "$TMP/places.db"
DATA_DIR="$TMP" alembic stamp head
DATA_DIR="$TMP" alembic revision --autogenerate -m check_drift
```
Resultado tras corregir el índice `idx_place_id`: el único ruido restante
son 10 falsos positivos, uno por cada columna `id INTEGER PRIMARY KEY
AUTOINCREMENT` (`search`, `place`, `review`, `place_image`,
`publication_queue`, `publication_queue_control`, `repair_queue`,
`repair_queue_control`, `search_result`, `openai_usage`). Es el patrón
conocido de Alembic con SQLite: una columna `INTEGER PRIMARY KEY` nunca
admite NULL de verdad (alias del rowid), pero SQLite no escribe `NOT NULL`
en el texto de `.schema` para ese caso concreto, así que la reflexión de
Alembic la ve como nullable mientras el modelo (con `primary_key=True`) la
espera `NOT NULL`. No es drift real y no se ha "corregido" — forzarlo
sería semánticamente incorrecto. El fichero de diagnóstico (`check_drift`)
se generó, se revisó y se borró; no es una migración real.

También se corrigieron dos cosas de ruido cosmético detectadas en el primer
intento: `sa.Float()` sustituido por `sa.REAL()` en todo el fichero (SQLite
usa afinidad `REAL`, y `Float` generaba un "type change" falso en el diff),
y las columnas que forman parte de una PK no entera
(`blog_article.place_id`/`lang`, `review_text.place_id`,
`place_featured_image.place_id`) marcadas `nullable=True` explícitamente,
porque la DDL real nunca declaró `NOT NULL` en ellas — otro quirk de SQLite
(una PK no entera no fuerza NOT NULL salvo que se declare a propósito).

## Pendiente (fuera de alcance hoy, por diseño)

Los siguientes pasos del plan (§6) quedan para más adelante:

- Paso 2: mantener SQLite detrás de la nueva capa (repositorios que usen
  `orm.py` en vez de `sqlite3` crudo).
- Paso 3: migrar cada caso de uso de `database.py` y los 9 ficheros
  restantes, con pruebas de equivalencia antes de eliminar los accesos
  directos a `sqlite3`.
- Investigar el origen real de `idx_place_id` y decidir si se documenta
  formalmente en `init_db()` o se aborda como parte de la limpieza de §7.

Ver `docs/postgresql-migration-plan.md` §18 (actualizado) para el estado
formal.
