# Hoja de ruta

Última actualización: 30 de julio de 2026.

## Fase 0: estabilizar el directorio gastronómico

Estado: casi completa. Queda un punto sin confirmar, el resto ya está
verificado en producción.

- Completar y observar la cola actual — hecho. Publicación (274) y
  reparación (127) drenadas, 0 pendientes, 0 errores definitivos.
- Validar publicaciones en varias ciudades — hecho. El catálogo cubre
  Mallorca, Madrid, Valladolid, A Coruña, Bérgamo (Italia) y más.
- Revisar errores, duplicados, títulos, imágenes y ACF — hecho.
  Auditorías repetidas el 23 y el 26 de julio
  (`docs/inventories/2026-07-26-content-quality-audit.md`), post huérfano
  resuelto, extractos con Markdown corregidos, títulos y retórica de
  artículos nuevos con más variedad.
- Añadir ciudades en lotes moderados — en marcha de forma continua vía la
  cola de publicación; no es un hito puntual que se pueda cerrar.
- Mantener copias de seguridad — hecho. Backup nuevo tomado el 26 de
  julio tras los cambios de esta sesión (checksum verificado en
  `docs/project-progress-summary.md` §19).
- Confirmar crecimiento de indexación e impresiones — **sin confirmar**.
  Requiere acceso a Search Console, que no está disponible desde aquí;
  solo lo puede revisar el operador.

No se debe hacer una gran refactorización mientras una publicación masiva esté activa.

## Fase 1: calidad y robustez

Estado: en marcha, 5 de 7 puntos completados (3 el 26 de julio, 2 más el
29 de julio de 2026). Solo quedan homogeneizar HTTP y timeouts/reintentos
sistemáticos.

- Homogeneizar respuestas y códigos HTTP — pendiente.
- Añadir timeouts y reintentos específicos a todas las integraciones —
  pendiente. Existe un timeout genérico en `wordpress.py`
  (`REQUEST_TIMEOUT = 60`), pero no es sistemático ni cubre reintentos.
- Evitar duplicados de lugares, reseñas e imágenes mediante restricciones
  — **hecho**. `review` tenía 81 filas duplicadas reales (16 fichas);
  desduplicadas y con índice único (`idx_review_unique`).
  `place_image` (`idx_place_image_unique`) y `place.place_id`
  (`idx_place_id`, ya existía en producción pero ahora declarado en
  `init_db()`) también protegidos, mismo patrón idempotente que
  `_ensure_columns()` (`docs/inventories/2026-07-26-integrity-and-logging.md`).
- Introducir migraciones de base de datos — **hecho**. Modelos
  SQLAlchemy fieles al esquema real + migración base de Alembic,
  verificados contra una copia de `places.db`
  (`docs/inventories/2026-07-26-sqlalchemy-alembic-baseline.md`). Es
  también el primer punto de la Fase 3 (ver abajo).
- Añadir pruebas unitarias y de integración con mocks — **parcialmente
  hecho**. 43 tests unitarios cubriendo la máquina de estados de las dos
  colas (`docs/inventories/2026-07-26-queue-tests.md`). Sin tests de
  integración HTTP ni mocks de OpenAI/WordPress/Google todavía.
- Añadir logs estructurados y métricas de costes — **hecho**. Métricas
  de coste de OpenAI implementadas
  (`docs/inventories/2026-07-24-openai-token-usage.md`). Las 39
  llamadas a `print()` que quedaban en el backend se sustituyeron por
  `logging` estándar con nivel, timestamp y módulo
  (`docs/inventories/2026-07-26-integrity-and-logging.md`).
- Crear proceso seguro de enriquecimiento histórico por lotes — hecho
  (la cola de reparación cubre este caso).

Resultado: un pipeline fiable que puede operar durante días sin supervisión constante.

## Fase 2: estructura pública del directorio

- Crear un plugin propio para CPT, taxonomías y Schema.org.
- Registrar municipio, provincia y tipo de comida como taxonomías.
- Refactorizar el tema propio para las plantillas del directorio.
- Generar páginas de ciudad como borradores.
- Listar restaurantes dinámicamente.
- Crear enlazado bidireccional.
- Añadir plantillas `single-restaurante.php`, `archive-restaurante.php` y
  `taxonomy-municipio.php` con tarjetas reutilizables.
- Añadir mapas, llamadas a la acción y metadatos Open Graph.
- Generar sitemap geográfico.
- Incorporar páginas regionales cuando haya suficiente cobertura.

Resultado: las fichas dejan de estar aisladas y forman un directorio navegable.

## Fase 3: núcleo multidirectorio

Estado: primer punto iniciado el 26 de julio de 2026 (ver Fase 1 arriba).

- Introducir SQLAlchemy y Alembic manteniendo primero SQLite — **iniciado**.
  Modelos y migración base ya existen y están verificados, pero la app
  sigue usando `sqlite3` crudo en los 10 ficheros de siempre; falta la
  capa de repositorios y migrar cada caso de uso con pruebas de
  equivalencia antes de poder decir que este punto está terminado
  (`docs/postgresql-migration-plan.md` §18).
- Ensayar y ejecutar la migración a PostgreSQL mediante el runbook documentado.
- Crear entidad `directory`.
- Registrar Dónde comer bien como primer proyecto.
- Asociar negocios, plantillas, cola y publicaciones a `directory_id`.
- Separar `business` de su participación en un directorio.
- Configurar destino WordPress por proyecto.
- Configurar mapeo de campos y taxonomías.
- Añadir selector de directorio en el panel.

Resultado: una instalación puede gestionar varios dominios sin duplicar código.

### Adelanto: siembra masiva por ciudad (30 de julio de 2026)

Antes de que exista la entidad `directory`, ya hay una pieza de
infraestructura pensada para ella: un pipeline que descubre los 20
mejores negocios de cada ciudad semilla (capital de provincia en España,
o una ciudad por estado en EEUU) contra Places API (New), con ranking por
rating/reseñas, coste acotado (Details solo para los 20 ya filtrados, no
para todos los candidatos descubiertos) y throttling reutilizando la
misma arquitectura de cola que `publication_queue`/`repair_queue`. El
sector buscado (restaurantes, peluquerías...) es un parámetro, no una
tabla nueva — evita adelantar el alcance de `directory`/`business_type`
antes de tener la capa de repositorios. Detalle completo en
`docs/inventories/2026-07-30-seed-queue.md`.

**Sin verificar todavía contra la API real de Google** (todo probado con
mocks y bases de datos temporales) ni desplegado a producción — pendiente
el rollout gradual documentado en el inventario (2-3 ciudades de prueba,
revisión manual, confirmar SKU de facturación en Google Cloud Console)
antes de lanzar las 102 ciudades semilla completas.

## Fase 4: asistente para nuevos directorios

El alta debe solicitar:

- Nombre, sector e idioma.
- Dominio y credenciales del CMS.
- Tipo de contenido y taxonomías.
- Campos del negocio.
- Plantilla editorial.
- Reglas de títulos.
- Ritmo de publicación.
- Territorio inicial.

El asistente debe crear un proyecto en borrador y ejecutar pruebas de conexión antes de permitir publicaciones.

### Criterio de salida: barra de calidad de monetización

Antes de dar por lanzado un directorio nuevo, debe cumplir los mismos
requisitos que permitieron aprobar AdSense en Dónde comer bien en menos
de una semana (26 de julio de 2026):

- Contenido original suficiente por ficha (no descripciones vacías ni
  genéricas).
- Navegación funcional: taxonomías, archivos y enlazado interno
  operativos, no solo fichas sueltas.
- Sin contenido fino ni duplicado — páginas con poco inventario en
  `noindex` hasta que tengan suficiente contenido propio.
- Página de privacidad y aviso legal publicados.

No es un requisito solo de SEO: condiciona si el directorio puede
monetizarse desde el primer día o si hay que esperar a una revisión
posterior de Google. Conviene comprobarlo con la misma auditoría que ya
existe (`scripts/audit-wordpress-content.php`) antes de solicitar
AdSense para un proyecto nuevo, no después.

## Fase 5: enriquecimiento y contacto comercial

- Capturar correo solo desde fuentes autorizadas y registrando procedencia.
- Permitir corrección manual de contacto.
- Registrar fecha de verificación.
- Detectar negocios sin web como posibles oportunidades.
- Crear un CRM ligero separado del contenido editorial.
- Respetar normativa de privacidad y comunicaciones comerciales.

No se debe mezclar automáticamente publicación editorial con campañas de contacto.

## Fase 6: escalabilidad

- Optimización, backups y observabilidad de PostgreSQL ya migrado.
- Worker separado con cola dedicada.
- Programación distribuida.
- Almacenamiento de objetos para imágenes.
- Roles y permisos.
- Auditoría.
- Límites y presupuesto por directorio.
- Panel de salud y costes.

## Próximas decisiones

Actualizado el 26 de julio de 2026 — la cola ya terminó (Fase 0 casi
completa, ver arriba). El orden recomendado ahora es cerrar lo que queda
de Fase 1 antes de seguir avanzando la Fase 3, porque son las piezas que
reducen riesgo en vez de añadir alcance nuevo:

1. Tomar una copia de seguridad nueva de `places.db` (la última verificada
   es del 23 de julio, y desde entonces ha habido cambios reales en
   producción).
2. Restricciones de integridad formales (`place_id` único ya existe sin
   documentar; faltan las de `review` e imágenes) y logs estructurados —
   los dos puntos de Fase 1 sin ningún avance todavía.
3. Capa de repositorios sobre los modelos SQLAlchemy ya creados, migrando
   casos de uso de `database.py` uno a uno con pruebas de equivalencia
   (Fase 3, siguiente paso natural tras la migración base).
4. Solo entonces, introducción de `directory` sin cambiar el
   comportamiento visible.

## Definición de producto a largo plazo

MyDirectoryTool será una plataforma privada para configurar, poblar, publicar y mantener directorios verticales, con conectores de fuentes y CMS reemplazables y automatización supervisada de extremo a extremo.

El plan técnico, la migración compatible y los criterios para lanzar el segundo
directorio están detallados en
[Transformación de MyDirectoryTool](mydirectorytool-transformation-plan.md).
