# Plan de implementación de WordPress

Este documento es el runbook para transformar Dónde comer bien en un directorio
estructurado sin perder publicaciones, URLs ni datos. Debe consultarse antes de
cualquier cambio en WordPress y actualizarse después de completar cada fase.

## 1. Decisiones cerradas

- Se mantiene el tema propio activo `dondecomerbien-theme`.
- No se usará GeneratePress ni `dondecomerbien-child`.
- La lógica estable del directorio vivirá en un plugin propio.
- El tema controlará únicamente la presentación pública.
- MyDirectoryTool seguirá siendo la fuente de automatización, contenido y datos.
- Las URLs actuales `/restaurantes/...` deben conservarse.
- Los cambios estructurales se probarán antes de modificar el diseño.
- Cada fase debe poder revertirse sin perder restaurantes.

## 2. Estado actual confirmado

Fecha del inventario: 23 de julio de 2026.

### Tema activo

```text
template=dondecomerbien-theme
stylesheet=dondecomerbien-theme
```

Ruta en la máquina:

```text
/home/guillem/docker/wp_dondecomerbien/wp_data/wp-content/themes/dondecomerbien-theme/
```

Archivos relevantes:

```text
functions.php
front-page.php
single-restaurante.php
archive-restaurante.php
style.css
```

El tema activo registra actualmente el CPT `restaurante` desde `functions.php`.
Su archivo usa:

```text
post type: restaurante
archive: activado
slug público: restaurantes
REST API: activada
```

### WordPress y Docker

```text
contenedor WordPress: wp_dondecomerbien_site
contenedor MySQL: wp_dondecomerbien_db
```

### Datos actuales

Las fichas utilizan el CPT `restaurante`, imagen destacada, contenido, excerpt y
campos ACF. MyDirectoryTool publica mediante REST y conserva el `wp_post_id`.

Campos ACF conocidos:

```text
telefono
web
email
codigo_postal
ciudad
municipio
provincia
region
pais
codigo_pais
distrito
latitud
longitud
tipo_de_comida
place_id
place_gallery
```

## 3. Arquitectura objetivo

```text
MyDirectoryTool
├── Google Places y selección
├── datos normalizados
├── generación de contenido e imágenes
├── cola y reintentos
└── publicación REST y ACF

Plugin mydirectorytool-core
├── CPT restaurante
├── taxonomía municipio
├── taxonomía provincia
├── taxonomía tipo de comida
├── sincronización ACF → taxonomías
├── Schema.org
└── reglas permanentes del directorio

Tema dondecomerbien-theme
├── diseño
├── single-restaurante.php
├── archive-restaurante.php
├── taxonomy-municipio.php
├── tarjetas reutilizables
├── mapas y botones
├── migas de pan
└── Open Graph visible
```

El plugin y el tema deben poder actualizarse de forma independiente. Cambiar el
tema no debe hacer desaparecer el CPT, las taxonomías ni los datos estructurados.

## 4. Regla de seguridad principal

No se editará únicamente la copia viva de WordPress. El código nuevo debe tener
una copia versionada en Git.

Estructura propuesta dentro de este repositorio:

```text
wordpress/
├── plugins/
│   └── mydirectorytool-core/
└── themes/
    └── dondecomerbien-theme/
```

La carpeta viva de `wp-content` será un destino de despliegue, no la única copia
del código. Nunca se subirán a Git credenciales, uploads, cachés ni copias SQL.

## 5. Fase 0: copia de seguridad e inventario

Estado: pendiente.

### Antes de empezar

1. Pausar la cola de MyDirectoryTool.
2. Esperar hasta que `processing` sea cero.
3. Anotar conteo de restaurantes publicados y pendientes.
4. Guardar una copia de SQLite y de los artículos/imágenes locales.
5. Exportar la base de datos de WordPress.
6. Copiar el tema activo, plugins personalizados y configuración ACF.
7. Verificar que los archivos de backup tienen contenido.

Destino recomendado:

```text
/home/guillem/backups/dondecomerbien/YYYY-MM-DD_HHMM/
```

Elementos mínimos:

```text
wordpress.sql
themes.tar.gz
plugins.tar.gz
acf-export.json
places.db
articles.tar.gz
images.tar.gz
```

No continuar si la copia SQL está vacía o si `places.db` no se puede abrir.

### Inventario que debe registrarse

- Tema y versión activos.
- Plugins activos y versiones.
- Versión de WordPress y PHP.
- Reglas de enlaces permanentes.
- Número de posts `restaurante` publicados, borradores y papelera.
- Grupo ACF y nombres exactos de campos.
- URLs de muestra que se usarán para las pruebas.

## 6. Fase 1: poner el código WordPress bajo Git

Estado: pendiente.

1. Crear `wordpress/themes/dondecomerbien-theme/` en este repositorio.
2. Copiar únicamente el código del tema activo.
3. Excluir archivos temporales, copias y recursos generados.
4. Crear `wordpress/plugins/mydirectorytool-core/`.
5. Documentar un procedimiento de despliegue reproducible.
6. Comparar siempre fuente y destino antes de sobrescribir la copia viva.

Resultado esperado: el tema puede reconstruirse desde Git aunque se pierda la
carpeta de Docker.

## 7. Fase 2: crear el plugin estructural

Estado: pendiente.

Nombre propuesto:

```text
MyDirectoryTool Core
slug: mydirectorytool-core
```

Estructura inicial:

```text
mydirectorytool-core/
├── mydirectorytool-core.php
├── includes/
│   ├── class-post-types.php
│   ├── class-taxonomies.php
│   ├── class-acf-sync.php
│   └── class-schema.php
└── README.md
```

### Migración segura del CPT

El plugin debe registrar exactamente:

```text
post type: restaurante
rewrite slug: restaurantes
has_archive: true
show_in_rest: true
supports: title, editor, thumbnail, excerpt
```

No se cambiarán el identificador ni el slug. Crear otro CPT provocaría que las
fichas existentes parezcan desaparecer.

Orden seguro:

1. Crear el plugin todavía inactivo.
2. Añadir temporalmente en el tema un fallback que solo registre el CPT cuando
   `post_type_exists('restaurante')` sea falso.
3. Hacer que el plugin registre el CPT con prioridad temprana.
4. Activar el plugin.
5. Regenerar las reglas de enlaces permanentes una sola vez.
6. Comprobar administración, REST, archivo y varias fichas.
7. Mantener el fallback durante un periodo corto de observación.
8. Eliminar el registro del tema cuando el plugin esté validado.

El plugin debe ejecutar `flush_rewrite_rules()` únicamente en activación y
desactivación, nunca en cada carga.

### Validación obligatoria

- `/restaurantes/` responde correctamente.
- Las URLs antiguas mantienen el mismo permalink.
- `/wp-json/wp/v2/restaurante` devuelve fichas.
- El menú Restaurantes sigue visible en administración.
- Crear o editar una ficha conserva imagen destacada y ACF.
- MyDirectoryTool puede publicar una ficha de prueba.

## 8. Fase 3: taxonomías

Estado: pendiente.

Taxonomías propuestas:

```text
municipio_restaurante
provincia_restaurante
tipo_comida_restaurante
```

Todas deben:

- Asociarse al CPT `restaurante`.
- Ser públicas.
- Tener archivos y URLs definidas.
- Exponerse en REST.
- Usar nombres y slugs estables.
- Mantener etiquetas legibles con acentos.

Antes de fijar los slugs públicos hay que decidir el formato final. Después de
indexarlos no deben cambiarse sin redirecciones 301.

### Fuente inicial de términos

```text
municipio_restaurante ← ACF municipio; si falta, ACF ciudad
provincia_restaurante ← ACF provincia
tipo_comida_restaurante ← ACF tipo_de_comida
```

No se eliminarán los campos ACF. ACF conserva el dato detallado y las taxonomías
aportan navegación, URLs, filtros y relaciones.

### Normalización

- Recortar espacios.
- Unificar diferencias de mayúsculas.
- Conservar la etiqueta correcta: `Sóller`, `Santa Ponça`, etc.
- Generar slugs con funciones nativas de WordPress.
- No mezclar municipio, distrito y provincia.
- Registrar y revisar términos dudosos antes de publicarlos.

## 9. Fase 4: sincronización histórica

Estado: pendiente.

El backfill debe ser idempotente: ejecutarlo dos veces no puede duplicar términos.

Procedimiento:

1. Implementar modo `dry-run` que no escriba.
2. Mostrar cuántas fichas se actualizarían y qué términos se crearían.
3. Revisar manualmente una muestra.
4. Ejecutar lotes de 10 o 20 fichas.
5. Registrar éxito, omisiones y errores por `post_id`.
6. Comparar conteos antes y después.
7. Repetir hasta que no queden fichas válidas sin términos.

No se debe ejecutar el backfill al mismo tiempo que una migración de base de
datos o un cambio grande en el pipeline.

### Publicaciones futuras

MyDirectoryTool deberá asignar términos al publicar, además de escribir ACF. El
plugin puede mantener una sincronización defensiva al guardar, pero el contrato
REST debe quedar documentado y probado.

## 10. Fase 5: refactor del tema propio

Estado: pendiente.

No se cambiará a GeneratePress. Se mejorará `dondecomerbien-theme`.

Estructura objetivo:

```text
dondecomerbien-theme/
├── functions.php
├── header.php
├── footer.php
├── front-page.php
├── single-restaurante.php
├── archive-restaurante.php
├── taxonomy-municipio_restaurante.php
├── taxonomy-provincia_restaurante.php
├── taxonomy-tipo_comida_restaurante.php
├── template-parts/
│   ├── card-restaurante.php
│   ├── restaurant-contact.php
│   └── breadcrumbs.php
├── assets/
│   ├── css/
│   └── js/
└── style.css
```

### `single-restaurante.php`

Debe mostrar:

- Título e imagen destacada.
- Contenido editorial.
- Tipo de comida.
- Dirección completa.
- Teléfono con enlace `tel:`.
- Web con `rel="noopener noreferrer"`.
- Mapa usando latitud y longitud, sin exponer claves privadas.
- Galería con dimensiones y textos alternativos.
- Municipio, provincia y enlaces a sus archivos.
- Restaurantes relacionados o cercanos.
- Migas de pan.

### `archive-restaurante.php`

Debe usar una tarjeta compartida y ofrecer:

- Imagen destacada con fallback.
- Título, localidad, tipo y extracto.
- Paginación accesible.
- Diseño responsive.
- Filtros que no generen infinitas URLs indexables sin control.

### Archivos territoriales

La plantilla de municipio debe incluir:

- Un único H1 útil: `Restaurantes en Sóller`.
- Texto introductorio editable.
- Listado de restaurantes del término.
- Enlaces a localidades o categorías relacionadas.
- Paginación y canonical correctos.

El CSS incrustado actualmente en las plantillas debe trasladarse progresivamente
a los assets del tema.

## 11. Fase 6: SEO técnico y compartición

Estado: pendiente.

### Open Graph

Cada ficha debe generar como mínimo:

```html
<meta property="og:type" content="article">
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:url" content="...">
<meta property="og:image" content="URL de la imagen destacada">
```

También deben añadirse `twitter:card`, `twitter:title`, `twitter:description` y
`twitter:image`. No deben duplicarse si otro plugin ya los genera.

Después de desplegar:

- Verificar el HTML público, no solo el editor.
- Comprobar que la imagen responde 200 y tiene tamaño suficiente.
- Considerar la caché de WhatsApp/Facebook al repetir pruebas.

### Schema.org

El plugin generará JSON-LD `Restaurant` usando datos reales:

```text
name
url
image
address
telephone
servesCuisine
geo.latitude
geo.longitude
```

No se inventarán horarios, precios ni valoraciones. No debe generarse más de una
entidad principal contradictoria por página.

### Enlazado interno

```text
provincia → municipios → restaurantes
restaurante → municipio/provincia/tipo
restaurante → restaurantes relacionados
```

## 12. Fase 7: pruebas

Estado: pendiente.

### Muestra mínima

Probar al menos:

- Una ficha con todos los campos.
- Una sin web.
- Una sin teléfono.
- Una sin distrito.
- Una sin imagen destacada.
- Una localidad con varios restaurantes.
- Una localidad con un solo restaurante.
- Una ficha nueva publicada por MyDirectoryTool.

### Navegadores y dispositivos

- Escritorio y móvil.
- Chrome/Brave y Firefox.
- Navegación con teclado.
- Imágenes lentas o ausentes.

### Comprobaciones técnicas

- Estado HTTP y redirecciones.
- Canonical.
- Un solo H1.
- Metadatos Open Graph.
- JSON-LD válido.
- REST API.
- Sitemap.
- Paginación.
- Enlaces internos.
- Ausencia de errores PHP y JavaScript.

## 13. Despliegue

Estado: pendiente.

Orden recomendado:

1. Pausar la cola.
2. Confirmar `processing = 0`.
3. Crear backup nuevo.
4. Desplegar plugin sin cambios visuales.
5. Activar y validar CPT/REST/URLs.
6. Migrar taxonomías en lotes.
7. Desplegar plantillas del tema.
8. Vaciar únicamente las cachés necesarias.
9. Ejecutar la lista de pruebas.
10. Publicar una ficha controlada.
11. Reanudar la cola.
12. Vigilar logs, portada, archivo y fichas durante las horas siguientes.

No mezclar en un único despliegue la migración del CPT, el backfill completo y
un rediseño visual grande.

## 14. Reversión

Si falla el plugin estructural:

1. Pausar la cola.
2. Activar o conservar el fallback del CPT en el tema.
3. Desactivar el plugin.
4. Regenerar enlaces permanentes.
5. Verificar que las fichas reaparecen con sus URLs originales.

Si falla el tema:

1. Restaurar la versión anterior versionada del tema.
2. No tocar el plugin ni los términos.
3. Vaciar caché y verificar fichas.

Si se corrompen datos:

1. Detener publicaciones y escrituras.
2. Conservar una copia del estado roto para diagnóstico.
3. Restaurar la base SQL verificada.
4. Restaurar `places.db` si también resultó afectada.
5. Comparar conteos y una muestra antes de reabrir la cola.

## 15. Criterios de finalización

La migración estructural estará terminada cuando:

- El CPT esté registrado exclusivamente por el plugin.
- Desactivar el tema no haga desaparecer los restaurantes en administración.
- Todas las URLs antiguas sigan funcionando.
- Municipio, provincia y tipo estén disponibles como taxonomías.
- Las fichas existentes tengan términos correctos o una excepción documentada.
- Las publicaciones nuevas asignen ACF y términos.
- Las plantillas usen componentes reutilizables.
- Open Graph muestre la imagen destacada al compartir.
- Schema.org se valide sin errores importantes.
- Exista backup, procedimiento de despliegue y reversión probado.

## 16. Registro de avance

Actualizar esta tabla después de cada sesión:

| Fase | Estado | Fecha | Commit / backup | Notas |
|---|---|---|---|---|
| 0. Backup e inventario | Completado | 2026-07-23 | Backup `2026-07-23_phase0` | Ver inventario versionado |
| 1. Código WordPress en Git | Completado | 2026-07-23 | Tema `e12c0ce`; plugin `6a087af` | Ambos repositorios publicados |
| 2. Plugin y migración CPT | Completado | 2026-07-23 | Backup `2026-07-23_pre_plugin_activation`; tema `e12c0ce`; plugin `6a087af` | Plugin activo y migración verificada |
| 3. Taxonomías | Completado | 2026-07-23 | Plugin `cd43c57` | Administración, REST, términos y archivos públicos verificados |
| 4. Backfill histórico | Completado | 2026-07-23 | Backup `2026-07-23_pre_taxonomy_sample`; plugin `649c177` | 248 fichas procesadas; verificación idempotente sin cambios |
| 5. Tema propio | En curso | 2026-07-23 | Tema `7dc7b29` | Archivos, tarjeta y ficha individual reutilizables desplegados |
| 6. SEO y Schema | Pendiente | | | |
| 7. Pruebas | Pendiente | | | |

## 17. Próxima acción exacta

La ficha individual y las galerías intercaladas están desplegadas. El siguiente
bloque continuará la fase del tema:

1. Incorporar canonical y metadatos sociales sin duplicar los de otro plugin.
2. Revisar en navegador el responsive de fichas, tarjetas y mapas.
3. Probar una muestra de fichas sin imagen, sin contacto y sin coordenadas.
4. Extraer contacto y migas a componentes independientes cuando se añada el
   segundo tipo de directorio.
5. Añadir descripciones editoriales a los términos territoriales prioritarios.

El fallback del tema se conservará durante la siguiente fase y se retirará en
una versión posterior, una vez comprobada la estabilidad del plugin.

### Avance del 23 de julio de 2026

- Backup e inventario completados y verificados.
- Tema activo publicado en su repositorio independiente.
- Plugin `mydirectorytool-core` 0.1.0 instalado en WordPress pero inactivo.
- Todos sus archivos PHP validados con PHP 8.2.
- WordPress lo detecta y conserva 248 restaurantes publicados.
- Repositorio local del plugin inicializado en `main`.
- Commit inicial del plugin: `3de04e8`.
- Remoto configurado:
  `git@github.com:canalenguillem/mydirectorytool-wp-plugin.git`.
- Plugin publicado en
  `git@github.com:canalenguillem/mydirectorytool-wp-plugin.git`.

### Preparación del CPT del 23 de julio de 2026

- El tema incorpora un fallback: solo registra `restaurante` si ningún plugin lo
  ha registrado previamente.
- El plugin incorpora el registro compatible del CPT en prioridad 5, con el
  mismo slug `restaurantes`, soportes y exposición REST actuales.
- Los hooks de activación y desactivación regeneran las reglas de enlaces
  permanentes.
- Se validó la sintaxis de los cuatro archivos PHP modificados.
- Con el plugin todavía inactivo se verificaron 248 restaurantes publicados,
  tema activo `dondecomerbien-theme`, archivo, ficha y REST con HTTP 200.
- Commits publicados: tema `e12c0ce`; plugin `6a087af`.

### Activación controlada del 23 de julio de 2026

- Backup previo creado en
  `/home/guillem/backups/dondecomerbien/2026-07-23_pre_plugin_activation/`.
- El backup contiene el volcado SQL, el tema y el plugin.
- El volcado se generó con `--no-tablespaces` y finalizó correctamente.
- Las firmas SHA-256 y los archivos comprimidos fueron verificados.
- `mydirectorytool-core` quedó activo.
- Prioridad del registro del plugin: 5.
- Prioridad del fallback del tema: 10.
- Se conservaron 248 restaurantes publicados.
- Home, archivo, ficha de muestra y endpoint REST respondieron HTTP 200.
- El CPT conserva el slug `restaurantes`, archivo público y REST activo.
- No aparecieron errores PHP en los logs de la ventana de activación.

La fase 2 se considera completada. El rollback sigue disponible mediante el
backup anterior y la desactivación del plugin, que devolvería el registro del
CPT al fallback del tema.

### Taxonomías estructurales del 23 de julio de 2026

- Plugin actualizado a la versión 0.2.0, commit `15fd83c`.
- Registradas `municipio_restaurante`, `provincia_restaurante` y
  `tipo_comida_restaurante`.
- Asociadas únicamente al CPT `restaurante`.
- Visibles en administración y expuestas mediante REST.
- Sus consultas y rewrites públicos están desactivados temporalmente.
- No se crearon términos ni se modificó ninguna ficha.
- Se conservaron los 248 restaurantes y las páginas públicas verificadas.
- El inventario de los campos ACF está en
  `docs/inventories/2026-07-23-taxonomy-dry-run.md`.

### Backfill histórico del 23 de julio de 2026

- Plugin actualizado a la versión 0.3.0, commit `649c177`.
- Motor paginado, idempotente y con modo `dry-run`.
- Backup SQL previo:
  `/home/guillem/backups/dondecomerbien/2026-07-23_pre_taxonomy_sample/`.
- Primera muestra de 10 fichas antiguas: sin ubicación, tipo asignado y campos
  vacíos omitidos correctamente.
- Segunda muestra de 10 fichas territoriales: municipio, provincia y tipo
  asignados correctamente.
- Backfill completo ejecutado en lotes sobre 248 fichas.
- Dry-run global posterior: 248 sin cambios y cero errores.
- Resultado: 67 municipios con 197 asignaciones, 18 provincias con 198
  asignaciones y 39 tipos de comida con 249 asignaciones.
- Las 249 asignaciones de tipo son correctas: una ficha recibió dos términos
  desde `mediterránea-italiana`.
- Portada, archivo, ficha y REST continuaron respondiendo HTTP 200.
- No se detectaron errores PHP en los logs.
- Informe completo en
  `docs/inventories/2026-07-23-taxonomy-backfill.md`.

### Archivos públicos de taxonomía del 23 de julio de 2026

- Tema actualizado, commit `136d1ff`.
- Plugin actualizado a la versión 0.4.1, commit `cd43c57`.
- Tarjeta de restaurante reutilizable por archivo general y taxonomías.
- Fallback visual para fichas sin imagen destacada.
- Plantilla compartida `taxonomy.php`.
- H1 contextual por municipio, provincia y tipo de comida.
- Paginación de 12 restaurantes por página.
- Las reglas específicas preceden a las reglas de adjuntos del CPT.
- URLs verificadas:
  - `/restaurantes/municipio/soller/`
  - `/restaurantes/provincia/illes-balears/`
  - `/restaurantes/tipo-comida/mediterranea/`
- Primera página y página 2 verificadas con HTTP 200.
- Archivo general, ficha individual y REST continúan con HTTP 200.
- Inventario del despliegue en
  `docs/inventories/2026-07-23-public-taxonomy-archives.md`.

### Ficha individual e imágenes intercaladas del 23 de julio de 2026

- Tema actualizado, commit `7dc7b29`, versión 1.2.
- Imagen destacada conservada al principio de la ficha.
- Galería dividida en parejas.
- Una pareja se inserta después de cada dos párrafos.
- Si quedan imágenes cuando terminan los párrafos, se muestran al final sin
  descartarlas.
- En móvil las parejas pasan a una sola columna.
- Se reutilizan los adjuntos de WordPress con `srcset` cuando están disponibles.
- La ficha muestra taxonomías, contacto, migas de pan y mapa OpenStreetMap.
- El mapa no necesita ni expone claves privadas.
- Ficha de Burdo validada con cinco parejas intercaladas y HTTP 200.
- Archivo y taxonomía de control continuaron con HTTP 200.
- Inventario en
  `docs/inventories/2026-07-23-interleaved-gallery.md`.
