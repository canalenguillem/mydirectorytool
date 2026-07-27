# Pruebas automatizadas para las colas de publicación y reparación

Fecha: 26 de julio de 2026.
Autor: sesión de Claude Code (en ausencia de Codex).

## Objetivo

`docs/project-progress-summary.md` §22 pedía desde hace tiempo "añadir
pruebas automatizadas para ambas colas". El proyecto no tenía ningún test
(sin `pytest`, sin `backend/tests/`). Con dos colas críticas corriendo sin
supervisión cada 5 minutos en producción, y todo el trabajo de esta sesión
verificado a mano artículo por artículo, era la tarea que más riesgo
reducía por el esfuerzo invertido — se priorizó sobre continuar con
PostgreSQL o el rediseño multi-directorio.

## Alcance

Se cubre la máquina de estados de ambas colas
(`backend/app/services/publication_queue.py`,
`backend/app/services/repair_queue.py`): encolar, pausar, reanudar,
reintentar, consultar estado, reclamar el siguiente elemento y cerrar un
intento (éxito, fallo con reintentos restantes, fallo definitivo).

**No se testea** `_run_pipeline`/`_repair_place` en sí — dependen de
OpenAI, WordPress, Google Places y el filesystem real; mockear las tres
integraciones habría costado mucho por poca señal adicional sobre lo ya
verificado a mano esta sesión. Tampoco se añaden tests de los routers
FastAPI ni CI — quedan como trabajo futuro natural, no parte de esto.

## Cambio en el código de producción (refactor sin cambio de comportamiento)

`_worker()` en ambos ficheros era un `while True` con `time.sleep(2)`,
imposible de invocar desde un test. Se extrajo el cuerpo de una iteración
a `_process_once()` (reclama, procesa, cierra — devuelve el `place_id`
procesado o `None`), y `_worker()` pasó a ser solo el bucle que la llama.
Mismo comportamiento exacto, solo nombrado y extraído — permite testear
"si el pipeline falla, ¿la cola pasa a pending/failed correctamente?" sin
tocar ninguna API externa, monkeypencheando `_run_pipeline` /
`_repair_place` directamente.

## Infraestructura de test

- `backend/requirements-dev.txt` (nuevo): `pytest>=8.0`. No se copia a la
  imagen Docker (`Dockerfile` solo instala `requirements.txt`), así que
  pytest no entra en producción.
- `backend/pytest.ini`: `pythonpath = .` — el proyecto no usa
  `__init__.py` en ningún paquete (namespace packages), así que hacía
  falta indicarle a pytest la raíz de imports explícitamente.
- `backend/tests/conftest.py`: fixture `temp_db` crea un SQLite temporal
  por test (`tmp_path`) y usa `monkeypatch` para redirigir `DB_PATH` en
  `database`, `publication_queue` y `repair_queue` al mismo fichero
  temporal, después llama a la función real `database.init_db()` (no un
  esquema reinventado a mano). Como Python resuelve `DB_PATH` en el
  namespace del módulo en el momento de la llamada y no al definir la
  función, monkeypatchear el atributo del módulo basta para redirigir
  `_connect()` sin tocar el resto del código. Helpers `insert_place()` y
  `add_fake_image()` para sembrar datos de prueba.
- `backend/tests/test_publication_queue.py` (21 tests),
  `backend/tests/test_repair_queue.py` (22 tests).

## Verificación

- `pytest -v`: **43/43 en verde**.
- Comprobación explícita de aislamiento: ejecutar con
  `DATA_DIR=/ruta/que/no/existe` falla alto y claro
  (`PermissionError` al importar) en vez de tocar datos reales en
  silencio — confirma que la ruta a `data/places.db` nunca se usa salvo
  que el proceso la reciba explícitamente.
- `md5sum`/`stat` de `data/places.db` idénticos antes y después de correr
  toda la suite — cero escrituras en la base real.
- Desplegado el refactor de `_process_once` en producción
  (`docker compose up -d --build backend`): arranque limpio, sin errores
  en los logs.

## Cómo ejecutar los tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

## Pendiente

- Tests de integración HTTP sobre `api/queue.py` / `api/repair_queue.py`.
- CI (GitHub Actions) que ejecute la suite en cada push — hoy solo corre
  en local, a mano.
- Cobertura de `database.py` (fuera de alcance hoy — es el fichero que se
  empezará a sustituir por la capa SQLAlchemy cuando avance el plan de
  PostgreSQL).
