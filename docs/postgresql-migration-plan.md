# Plan de migración de SQLite a PostgreSQL

Este documento define la futura migración de la base de datos de MyDirectoryTool.
No autoriza ni inicia ninguna migración. La cola actual debe continuar usando
SQLite hasta que el directorio gastronómico esté estabilizado y exista un ensayo
completo sobre una copia.

## 1. Decisión

- MyDirectoryTool migrará de SQLite a PostgreSQL.
- WordPress seguirá usando su propia base MySQL.
- No se compartirán base, usuario ni credenciales entre WordPress y la aplicación.
- PostgreSQL se incorporará al comenzar el núcleo multidirectorio, no durante la
  publicación masiva actual.
- La migración definitiva tendrá una ventana corta y controlada con la cola
  pausada, pero los ensayos se realizarán sin afectar producción.

## 2. Motivo

SQLite ha sido adecuado para el MVP porque existe un único operador, un backend
y un worker. El producto multidirectorio necesitará:

- Configuración y credenciales aisladas por proyecto.
- Colas independientes.
- Más relaciones y restricciones.
- Migraciones de esquema versionadas.
- Auditoría y métricas.
- Operaciones concurrentes y futuros workers separados.
- Consultas territoriales y administrativas más complejas.

La migración no se justifica por los cientos de fichas actuales, sino por el
modelo operativo futuro.

## 3. Alcance

Se migrarán los datos relacionales de MyDirectoryTool:

```text
search
search_result
place / business
review
review_text
blog_article
place_image
place_featured_image
publication_queue
publication_queue_control
futuras tablas directory y directory_business
```

No se moverán a PostgreSQL:

```text
data/articles/
data/images/
uploads de WordPress
base MySQL de WordPress
credenciales en texto plano
```

Los archivos continuarán en almacenamiento persistente y la base guardará sus
rutas o identificadores.

## 4. Arquitectura objetivo

```text
Frontend
   │
FastAPI
   │
SQLAlchemy / repositorios
   │
PostgreSQL

Worker de publicación
   │
misma capa de repositorios
   │
PostgreSQL
```

Tecnología recomendada:

- SQLAlchemy 2 para acceso a datos.
- Alembic para migraciones versionadas.
- Driver PostgreSQL compatible con el modo de ejecución elegido.
- `DATABASE_URL` como referencia de conexión.
- Contenedor PostgreSQL con versión estable fijada explícitamente cuando se
  implemente; no utilizar `latest`.

## 5. Condiciones previas

No empezar la migración hasta cumplir:

- Backup verificado de `places.db` y archivos.
- Cola actual completada o en una fase estable.
- Sistema de migraciones introducido.
- Pruebas del pipeline, cola, publicación y borrado.
- Modelo `directory` acordado.
- Restricciones y claves únicas documentadas.
- Inventario de tablas, columnas, índices y conteos.
- Entorno PostgreSQL de ensayo separado.

## 6. Estrategia: capa de datos antes que cambio de motor

El código actual usa `sqlite3` directamente. No conviene sustituir consultas y
motor al mismo tiempo en un único despliegue.

Orden:

1. Crear modelos y repositorios con SQLAlchemy.
2. Mantener temporalmente SQLite detrás de esa capa.
3. Migrar cada caso de uso y añadir pruebas de equivalencia.
4. Eliminar accesos directos dispersos a `sqlite3`.
5. Introducir Alembic y representar el esquema actual como migración base.
6. Ejecutar las mismas pruebas con SQLite y PostgreSQL.
7. Migrar los datos únicamente cuando la aplicación sea agnóstica al motor.

La aplicación no debe contener SQL específico de PostgreSQL salvo en módulos
aislados y justificados.

## 7. Normalización previa del esquema

Antes de exportar:

- Resolver duplicados de `place_id`.
- Añadir claves únicas necesarias.
- Revisar filas huérfanas.
- Normalizar booleanos y estados.
- Definir timestamps con zona horaria cuando corresponda.
- Sustituir valores vacíos ambiguos por `NULL` cuando sea correcto.
- Verificar rutas de artículos e imágenes.
- Definir claves foráneas y política de borrado.
- Incorporar `directory_id` mediante una migración planificada.

Reglas mínimas futuras:

```text
business.google_place_id                         UNIQUE
directory.slug                                  UNIQUE
directory_business(directory_id, business_id)   UNIQUE
publication_job.idempotency_key                  UNIQUE
```

## 8. Conversión de tipos

Revisar explícitamente:

| SQLite | PostgreSQL recomendado |
|---|---|
| `INTEGER` usado como booleano | `BOOLEAN` |
| segundos Unix | `TIMESTAMPTZ` o conversión documentada |
| `REAL` para coordenadas | `DOUBLE PRECISION` o `NUMERIC` acordado |
| texto JSON futuro | `JSONB` cuando necesite consultas |
| IDs incrementales | `BIGINT GENERATED ...` o identidad equivalente |
| estados de texto | `VARCHAR` con `CHECK` o tabla de estados |

No convertir automáticamente sin revisar semántica y valores reales.

## 9. Herramienta de transferencia

Crear un comando propio, repetible y auditable:

```text
python -m app.migrations.sqlite_to_postgres \
  --source /data/places.db \
  --target-env DATABASE_URL \
  --dry-run
```

Debe:

- Abrir SQLite en modo lectura.
- Comprobar versión de esquema.
- Migrar en orden de dependencias.
- Usar transacciones por fase o una transacción completa según el volumen.
- Conservar IDs cuando sea necesario.
- Registrar conteos sin mostrar secretos.
- Fallar ante duplicados o referencias inválidas.
- Poder ejecutarse sobre una base PostgreSQL vacía de ensayo.
- No duplicar datos si se repite accidentalmente.

No se hará una colección de `INSERT` manuales sin validación.

## 10. Ensayo

El ensayo no afecta a la cola activa:

1. Copiar `places.db` a un directorio temporal seguro.
2. Crear PostgreSQL de ensayo vacío.
3. Aplicar migraciones Alembic.
4. Ejecutar transferencia en `dry-run`.
5. Corregir advertencias.
6. Ejecutar transferencia real sobre ensayo.
7. Iniciar una copia del backend contra PostgreSQL de ensayo, sin worker o con
   publicación externa desactivada.
8. Ejecutar pruebas de lectura y escritura controladas.
9. Destruir únicamente el entorno de ensayo cuando el informe esté guardado.

Realizar al menos dos ensayos exitosos a partir de copias diferentes antes del
corte definitivo.

## 11. Validación de datos

Comparar por tabla:

- Número de filas.
- IDs mínimos y máximos.
- Nulos en campos obligatorios.
- Duplicados de claves naturales.
- Estados de cola.
- Relaciones huérfanas.
- Sumas o hashes estables de columnas seleccionadas.

Muestras funcionales:

- Un negocio pendiente.
- Uno publicado.
- Uno con error de cola.
- Uno con reseñas, artículo e imágenes.
- Uno sin teléfono o web.
- Negocios de varias ciudades.

Pruebas de aplicación:

- Login.
- Listado y filtros.
- Búsqueda guardada.
- Guardar y eliminar una ficha de prueba.
- Encolar, pausar y reanudar sin publicar externamente en ensayo.
- Generar contenido con conectores simulados.
- Comprobar idempotencia.

## 12. Corte definitivo

Solo cuando los ensayos estén aprobados:

1. Anunciar ventana de mantenimiento.
2. Pausar la cola.
3. Esperar `processing = 0`.
4. Detener escrituras del backend.
5. Copiar `places.db` y verificar la copia.
6. Crear o limpiar la base PostgreSQL de producción mediante un procedimiento
   exacto y revisado.
7. Aplicar migraciones Alembic.
8. Transferir desde la copia final de SQLite.
9. Ejecutar todas las validaciones de conteo e integridad.
10. Cambiar `DATABASE_URL`.
11. Arrancar backend con el worker todavía pausado.
12. Ejecutar pruebas de humo.
13. Activar el worker con un único trabajo controlado.
14. Vigilar logs y estados.
15. Reanudar el ritmo normal.

No borrar ni modificar el SQLite original durante el corte.

## 13. Reversión

Si falla antes de reanudar la cola:

1. Detener el backend nuevo.
2. Restaurar la configuración SQLite anterior.
3. Arrancar el backend con la cola pausada.
4. Comprobar conteos y estado.
5. Reanudar solo cuando la aplicación original esté validada.

Si PostgreSQL ya aceptó nuevas escrituras, no volver automáticamente a SQLite:
primero hay que identificar y exportar las diferencias. El criterio de rollback
debe fijar un punto de no retorno antes del corte.

Conservar:

- SQLite final en modo solo lectura.
- Export SQL de PostgreSQL posterior al corte.
- Logs e informe de migración.
- Commit y versiones exactas desplegadas.

## 14. Backups de PostgreSQL

Antes de considerarlo producción:

- Backup automatizado periódico.
- Retención definida.
- Copia fuera del volumen principal.
- Prueba de restauración.
- Monitorización de espacio.
- Credenciales de backup separadas cuando sea posible.

Un backup no se considera válido hasta que se ha restaurado en un entorno de
prueba.

## 15. Docker y configuración

El servicio PostgreSQL debe:

- Usar volumen persistente explícito.
- No publicar su puerto al exterior salvo necesidad local controlada.
- Tener healthcheck.
- Recibir secretos fuera de Git.
- Fijar versión mayor y estrategia de actualización.
- Limitar conexiones y recursos de forma razonable.

Variables conceptuales:

```text
DATABASE_URL
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
```

No reutilizar las credenciales MySQL de WordPress.

## 16. Observabilidad posterior

Medir:

- Conexiones activas.
- Consultas lentas.
- Tamaño de base e índices.
- Errores de transacción.
- Bloqueos.
- Duración de trabajos de cola.
- Estado y antigüedad del último backup.

## 17. Criterios de finalización

- No quedan accesos productivos directos a `sqlite3`.
- Alembic representa todo el esquema.
- Dos ensayos completos han pasado.
- Conteos e integridad coinciden.
- Pipeline y borrado funcionan con PostgreSQL.
- Cola multidirectorio usa transacciones seguras.
- Backups y restauración están probados.
- SQLite final está archivado y documentado.
- WordPress continúa usando MySQL sin cambios.

## 18. Estado y próxima acción

Estado: **planificada, no iniciada**.

La próxima acción no es instalar PostgreSQL. Primero se deben introducir
migraciones formales y una capa de repositorios mientras la aplicación continúa
funcionando con SQLite. La ejecución se programará al comenzar el núcleo
multidirectorio y después de estabilizar la cola actual.
