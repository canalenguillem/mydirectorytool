# Arquitectura

## Vista general

```text
Navegador
   │
   ▼ :8091
Nginx + React
   │ /api
   ▼
FastAPI ─────────────── SQLite + archivos en /data
   │                         │
   ├── Google Places         ├── places.db
   ├── OpenAI                ├── articles/
   └── WordPress + ACF       ├── images/
                             └── exports/
```

## Frontend

Tecnologías:

- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- Nginx para producción y proxy `/api`.

Responsabilidades:

- Login y comprobación de sesión.
- Búsqueda y selección de negocios.
- Visualización de guardados y publicados.
- Ejecución manual del pipeline por ficha.
- Control y seguimiento de la cola.

## Backend

Tecnologías:

- FastAPI.
- Python.
- SQLite mediante `sqlite3`.
- Servicios síncronos para integraciones externas.

Módulos principales:

```text
app/api/auth.py               autenticación
app/api/places.py             búsquedas, guardado, reseñas e imágenes
app/api/blog.py               publicación y gestión de WordPress
app/api/queue.py              control de la cola
app/models/database.py        esquema y operaciones SQLite
app/services/google_places.py Google Places
app/services/openai_writer.py generación editorial
app/services/place_images.py  descarga de imágenes
app/services/wordpress.py     posts, medios y ACF
app/services/publication_queue.py worker persistente
```

## Flujo de una búsqueda

```text
Consulta del usuario
→ Text Search de Google
→ una llamada Place Details por resultado
→ search_result
→ selección manual
→ place
```

Buscar no implica guardar. Guardar no implica publicar inmediatamente.

## Flujo del pipeline

```text
place pendiente
→ reseñas y datos de ficha
→ artículo en caché o generación con OpenAI
→ imágenes en caché o descarga
→ imagen destacada
→ publicación en WordPress
→ campos ACF
→ marcado local como publicado
```

## Flujo de la cola

```text
pending
→ processing
→ completed
     o
→ pending (reintento)
     o
→ failed (tras 3 intentos)
```

El control de la cola guarda si está activa, intervalo y próxima ejecución. Los trabajos interrumpidos vuelven a `pending` al arrancar el backend.

## Persistencia

El volumen `./data:/data` mantiene la base y los archivos fuera de los contenedores. Reconstruir una imagen Docker no elimina el contenido del directorio `data/`.

## Seguridad actual

- Cookie de sesión firmada.
- Contraseña y secreto fuera del repositorio.
- Backend no publicado en el host.
- WordPress usa usuario y contraseña de aplicación.
- Archivos de datos y credenciales ignorados por Git.

## Evolución recomendada

Cuando aumenten volumen y proyectos:

- Migrar de SQLite a PostgreSQL siguiendo el
  [runbook de migración](postgresql-migration-plan.md).
- Separar API y worker.
- Introducir migraciones versionadas.
- Cifrar credenciales de cada directorio.
- Añadir auditoría de acciones y publicaciones.
- Aplicar rate limiting y permisos por usuario.
- Añadir tests de contratos para Google, OpenAI y WordPress.

## Frontera con WordPress

La herramienta gestiona datos, generación y publicación; un plugin propio
mantiene el modelo público del directorio (CPT, taxonomías y Schema.org); y el
tema propio controla las plantillas y el diseño. La decisión completa y el orden
de implementación están documentados en
[Arquitectura de WordPress](wordpress-integration.md).
