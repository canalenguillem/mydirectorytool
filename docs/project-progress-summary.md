# Resumen completo del proyecto MyDirectoryTool

Última actualización: 23 de julio de 2026.

Este documento es el punto de reentrada rápido al proyecto. Resume la visión,
la arquitectura, todo lo construido, las correcciones realizadas, el estado
operativo y el siguiente trabajo recomendado.

## 1. Objetivo

MyDirectoryTool comenzó como una herramienta para buscar restaurantes en Google
Maps y publicar artículos en `dondecomerbien.com`. El objetivo actual es
convertirlo en una plataforma reutilizable para lanzar directorios de distintos
sectores, por ejemplo peluquerías, con pocos pasos:

1. comprar y dirigir un dominio al servidor;
2. crear una instalación de WordPress;
3. instalar el tema y el plugin propios;
4. configurar el token de aplicación de WordPress;
5. crear el directorio desde MyDirectoryTool;
6. seleccionar negocios;
7. enriquecer datos, generar contenido y publicar mediante colas;
8. generar navegación territorial y temática;
9. medir indexación, impresiones, CTR y visitas.

El primer directorio real sigue siendo **Dónde comer bien**.

## 2. Repositorios

### Aplicación principal

```text
git@github.com:canalenguillem/mydirectorytool.git
```

Contiene backend, frontend, SQLite, publicación, colas, scripts y
documentación.

### Tema de WordPress

```text
git@github.com:canalenguillem/mydirectorytool-wp-theme.git
```

Tema propio y reutilizable. No depende de GeneratePress.

Estado actual:

- nombre: `Donde Comer Bien`;
- versión: 1.5;
- último cambio relevante: commit `2dd9d91`.

### Plugin de WordPress

```text
git@github.com:canalenguillem/mydirectorytool-wp-plugin.git
```

Núcleo estructural que debe permanecer aunque se cambie de tema.

Estado actual:

- nombre: `MyDirectoryTool Core`;
- versión: 0.5.2;
- último cambio relevante: commit `3ee1cf7`.

## 3. Arquitectura operativa

```text
Navegador
   │
   ▼
Frontend React + Nginx :8091
   │ red interna Docker
   ▼
Backend FastAPI :8090
   ├── SQLite
   ├── Google Places
   ├── OpenAI
   └── REST API de WordPress
                         │
                         ▼
                WordPress + ACF
                         │
                         ▼
              Tema + plugin propios
```

Solo el puerto `8091` está publicado en el host. El backend permanece dentro de
la red de Docker.

El Nginx externo sirve `dondecomerbien.com` por HTTPS y reenvía WordPress a:

```text
http://192.168.1.40:8085
```

## 4. Acceso y seguridad

- Login privado del panel para `enguillem`.
- Sesión firmada mediante cookie `HttpOnly`.
- Credenciales y secretos en archivos de entorno excluidos de Git.
- Backend no expuesto directamente.
- WordPress se conecta mediante usuario y contraseña de aplicación.
- Las operaciones destructivas del panel eliminan post, medios y registro
  local de manera coordinada.

## 5. Descubrimiento de negocios

- Búsqueda mediante Google Places.
- Los resultados no se guardan automáticamente.
- Se puede guardar un resultado sin abandonar la búsqueda.
- Los resultados guardados quedan identificados.
- Filtro textual sobre negocios guardados.
- Filtro de puntuación, incluido “menos de 4”.
- Eliminación mediante una cruz roja visible sin desplegar la ficha.
- Se redujeron llamadas duplicadas a Google.
- Los errores puntuales de detalles no descartan todos los resultados.

## 6. Datos almacenados

Para cada negocio se conservan, cuando están disponibles:

- nombre;
- dirección;
- Place ID;
- valoración;
- teléfono;
- web;
- email y procedencia del email;
- código postal;
- país y código de país;
- región;
- provincia;
- municipio;
- ciudad;
- distrito;
- latitud y longitud;
- estado operativo;
- tipo de comida;
- artículo local;
- imágenes e imagen destacada;
- ID y URL de WordPress.

Google Places no proporciona correos electrónicos. No hay scraping automático
de webs y no se inventan datos ausentes.

## 7. Contenido

- Obtención y almacenamiento de reseñas.
- Generación de artículos con OpenAI.
- Artículos Markdown guardados en caché.
- Recuperación o regeneración cuando una ruta histórica ya no existe dentro
  del volumen Docker.
- Generación de extractos.
- Clasificación del tipo de comida.
- Veinte estructuras deterministas para reducir títulos repetitivos.
- Limpieza de bloques SEO y Markdown no deseados antes de publicar.
- Prevención de un H1 duplicado dentro del cuerpo del artículo.

## 8. Imágenes

- Descarga de fotografías desde Google Places.
- Registro local sin repetir filas ya existentes.
- Elección de imagen destacada.
- Optimización previa a WordPress cuando el archivo es demasiado grande.
- Una sola subida de la destacada.
- Galería asociada al post y guardada en ACF.
- Imagen destacada en la parte superior de la ficha.
- Galería intercalada cada dos párrafos.
- Parejas de imágenes en la misma fila en pantallas grandes.
- Una columna en móvil.
- Reutilización de adjuntos y `srcset` cuando WordPress los ofrece.

## 9. Publicación en WordPress

- Tipo de contenido propio: `restaurante`.
- Publicación de título, contenido, extracto, destacada y galería.
- Escritura de todos los campos ACF conocidos.
- Registro local del nuevo ID y permalink.
- Protección frente a republicaciones accidentales.
- Opción para volver a publicar si el post histórico fue eliminado.
- Pipeline manual completo:

```text
reseñas → artículo → imágenes → destacada → WordPress
```

- Pipeline de reparación para recuperar y republicar una ficha borrada.

## 10. Plugin de WordPress

El plugin es responsable de la estructura que no debe depender del diseño:

- registro del CPT `restaurante`;
- taxonomía de municipio;
- taxonomía de provincia;
- taxonomía de tipo de comida;
- backfill idempotente desde campos ACF;
- sincronización automática de taxonomías después de guardar ACF;
- canonical;
- Open Graph;
- Twitter Cards;
- JSON-LD `Restaurant`;
- política de indexación para archivos débiles;
- sitemaps de contenido y taxonomías.

Un backfill idempotente puede ejecutarse varias veces: solo aplica diferencias
y no duplica términos ni relaciones.

## 11. Tema de WordPress

El tema controla exclusivamente la presentación:

- portada del directorio;
- archivo general de restaurantes;
- ficha individual;
- páginas de municipio, provincia y tipo;
- tarjetas reutilizables;
- navegación `Restaurantes` y `Explorar`;
- barra de exploración también dentro de páginas municipales;
- migas de pan;
- contacto;
- galería intercalada;
- mapa OpenStreetMap;
- enlaces internos;
- diseño adaptable a móvil y escritorio.

La ficha muestra ahora:

```text
población · código postal
```

Ejemplo validado:

```text
Sa Coma · 07560
```

## 12. Páginas territoriales y temáticas

Se publicaron archivos navegables:

```text
/restaurantes/
/restaurantes/municipio/{slug}/
/restaurantes/provincia/{slug}/
/restaurantes/tipo-comida/{slug}/
```

Se añadieron descripciones editoriales prioritarias para municipios, provincias
y tipos de comida con inventario suficiente.

La portada enlaza automáticamente municipios y tipos destacados. Los enlaces
se recalculan cuando cambian los conteos.

## 13. SEO

- Canonical en archivos, taxonomías y paginación.
- Canonical nativo conservado en fichas individuales.
- Open Graph y Twitter Cards.
- Imagen destacada al compartir.
- Schema.org `Restaurant` con datos reales.
- Sitemaps XML comprobados.
- `robots.txt` anuncia el sitemap.
- Páginas de taxonomía con menos de tres fichas y sin descripción:
  `noindex, follow`.
- Esas páginas siguen siendo navegables, pero no aparecen en el sitemap.
- Taxonomías con inventario suficiente o contenido editorial son indexables.

Search Console mostró las primeras impresiones y clics. Se aplicó una muestra
controlada de diez títulos más breves sin cambiar slugs, URLs ni canonicals.

## 14. Auditoría y datos incompletos

Existe un auditor reutilizable y de solo lectura:

```text
scripts/audit-wordpress-content.php
```

Comprueba:

- destacada;
- galería;
- contacto;
- ubicación;
- extractos;
- longitud del contenido;
- títulos largos;
- fórmulas repetidas;
- duplicados exactos;
- taxonomías con poco inventario.

El panel dispone de una tarjeta `Incompletos` y filtros por:

- contacto;
- ubicación;
- imágenes;
- tipo de comida;
- artículo ausente en WordPress.

Cada tarjeta explica sus carencias mediante etiquetas.

La ubicación se considera incompleta si falta alguno de estos grupos:

- municipio o ciudad;
- coordenadas;
- código postal;
- código de país.

El botón `Actualizar datos desde Google`:

1. hace una sola petición de detalles;
2. rellena únicamente campos vacíos;
3. conserva correcciones manuales;
4. actualiza ACF si el artículo existe;
5. provoca la sincronización automática de taxonomías.

## 15. Cola de publicación

Cola persistente en SQLite para negocios nuevos:

- intervalo predeterminado: cinco minutos;
- máximo de tres intentos;
- pausa y reanudación;
- recuperación tras reiniciar Docker;
- lote de prueba;
- incorporación de todos los pendientes;
- tiempo estimado;
- trabajo actual;
- errores recientes;
- reintento de fallos;
- protección frente a dos workers en el mismo proceso.

No hace falta dejar el navegador abierto.

## 16. Cola de reparación

Cola separada para evitar revisar manualmente todas las fichas incompletas.

Para cada ficha ejecuta solo lo necesario:

1. enriquecer contacto y geografía;
2. recuperar el tipo de comida;
3. descargar imágenes si faltan;
4. sincronizar ACF;
5. recuperar o regenerar artículos históricos;
6. volver a publicar únicamente si el post fue eliminado.

Características:

- persistente en SQLite;
- una ficha cada cinco minutos;
- máximo de tres intentos;
- pausa y reanudación;
- errores recientes;
- reintentos;
- recuperación tras reiniciar Docker.

La primera reparación validada fue `Ca'n Pintxo Restaurant`:

- nuevo post ID 3775;
- nueva URL guardada;
- HTTP 200.

## 17. Estado operativo al redactar este resumen

Los contadores cambian mientras trabajan las colas.

Actualización del 24 de julio de 2026: las dos colas iniciales terminaron. La
publicación completó 244 trabajos sin errores y la reparación completó sus 92
trabajos sin errores definitivos. WordPress quedó con 315 restaurantes
publicados.

### Aplicación

| Métrica | Valor |
|---|---:|
| Negocios locales guardados | 348 |
| Marcados localmente como publicados | 283 |
| Fichas locales incompletas | 118 |

### WordPress

| Métrica | Valor |
|---|---:|
| Restaurantes publicados reales | 282 |

### Publicación automática

| Estado | Valor |
|---|---:|
| Activa | Sí |
| Pendientes | 31 |
| Procesando | 0 |
| Terminados | 213 |
| Errores definitivos | 0 |

### Reparación automática

| Estado | Valor |
|---|---:|
| Activa | Sí |
| Pendientes | 87 |
| Procesando | 0 |
| Terminados | 5 |
| Errores definitivos | 0 |

Las dos colas continúan aunque el navegador esté cerrado.

## 18. Discrepancias históricas conocidas

WordPress y SQLite pueden mostrar conteos distintos cuando:

- se elimina un post directamente desde WordPress;
- queda una referencia local a ese post;
- existe un post de WordPress sin registro local.

Se inventariaron ocho referencias históricas a posts eliminados y un post
huérfano. La cola de reparación sustituye progresivamente los IDs y URLs de las
referencias que se vuelven a publicar.

No debe marcarse masivamente todo como pendiente, porque eso podría republicar
negocios eliminados deliberadamente.

## 19. Backups principales

```text
/home/guillem/backups/dondecomerbien/2026-07-23_phase0/
/home/guillem/backups/dondecomerbien/2026-07-23_pre_plugin_activation/
/home/guillem/backups/dondecomerbien/2026-07-23_pre_taxonomy_sample/
/home/guillem/backups/dondecomerbien/2026-07-23_pre_term_descriptions/
/home/guillem/backups/dondecomerbien/2026-07-23_pre_title_sample/
/home/guillem/backups/dondecomerbien/2026-07-23_pre_repair_queue/
```

Backup previo a la cola de reparación:

```text
places.db
SHA-256: 5e118dbd5ca9428b07bd7b516a6810be16881d484920e5193ebd4fd4756008e4
```

## 20. Decisiones de arquitectura

- No usar GeneratePress.
- Tema propio reutilizable para distintos directorios.
- Plugin propio para CPT, taxonomías, Schema y reglas independientes del tema.
- MyDirectoryTool recopila, genera, publica y mantiene.
- WordPress presenta, indexa y sirve el directorio público.
- No depender exclusivamente de ACF para navegación territorial.
- Mantener URLs publicadas durante cambios editoriales.
- Separar cola de publicación y cola de reparación.
- Migrar SQLite a PostgreSQL antes de convertir la herramienta en un servicio
  multidirectorio con mayor concurrencia.

## 21. Transformación pendiente a plataforma multidirectorio

La aplicación todavía contiene conceptos específicos de restaurantes. Para
crear directorios de peluquerías u otros sectores se debe introducir:

- entidad `directory_project`;
- configuración por dominio y WordPress;
- credenciales por proyecto;
- esquema de campos por sector;
- plantillas de prompts por sector;
- taxonomías configurables;
- tipos de Schema configurables;
- colas asociadas a proyecto;
- asistente de alta de un nuevo directorio;
- migraciones formales;
- PostgreSQL;
- workers independientes del proceso web;
- pruebas automatizadas y CI.

El tema debe parametrizar textos como `Restaurantes`, iconos, colores y nombre
del CPT visible. El plugin debe registrar la estructura según la configuración
del proyecto, no mediante código duplicado.

## 22. Próximos pasos recomendados

1. Dejar terminar las colas actuales y revisar errores definitivos.
2. Repetir la auditoría de WordPress al finalizar.
3. Reconciliar de nuevo IDs y URLs entre SQLite y WordPress.
4. Comprobar cuántas fichas siguen incompletas porque Google no ofrece el dato.
5. Revisar visualmente una muestra de fichas reparadas.
6. No aplicar todavía el resto de títulos en bloque; medir primero la muestra
   en Search Console.
7. Añadir pruebas automatizadas para ambas colas.
8. Empezar la migración prevista a PostgreSQL.
9. Crear `directory_project` y eliminar configuraciones globales.
10. Preparar el asistente para lanzar un segundo directorio.

## 23. Documentación relacionada

- `docs/current-state.md`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/operations.md`
- `docs/content-and-seo.md`
- `docs/wordpress-integration.md`
- `docs/wordpress-implementation-plan.md`
- `docs/mydirectorytool-transformation-plan.md`
- `docs/postgresql-migration-plan.md`
- `docs/roadmap.md`
- `docs/inventories/`
