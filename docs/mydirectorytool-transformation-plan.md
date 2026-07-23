# Transformación de MyDirectoryTool en una plataforma multidirectorio

Este documento define cómo evolucionar el gestor actual de Dónde comer bien
hacia una herramienta privada capaz de configurar, poblar y mantener nuevos
directorios verticales con pocos pasos y sin duplicar código.

Debe utilizarse junto con:

- [Arquitectura de WordPress](wordpress-integration.md).
- [Plan de implementación de WordPress](wordpress-implementation-plan.md).
- [Modelo de datos](data-model.md).
- [Hoja de ruta](roadmap.md).

## 1. Objetivo del producto

Una vez preparada una instalación de WordPress, el operador debe poder crear un
directorio desde MyDirectoryTool mediante este flujo:

```text
Nuevo directorio
→ elegir sector o plantilla
→ indicar nombre, dominio y territorio
→ conectar WordPress
→ comprobar plugin, tema, REST y permisos
→ revisar campos, categorías y ritmo
→ ejecutar una publicación de prueba
→ activar el directorio
→ buscar y seleccionar negocios
→ publicar progresivamente
```

Ejemplos:

```text
Dónde comer bien       → restaurantes
Peluquerías Mallorca   → peluquerías
Talleres de confianza  → talleres
Gimnasios cercanos     → gimnasios
```

## 2. Qué significa “pocos clics”

### Primera versión alcanzable

El operador realiza fuera de MyDirectoryTool:

1. Comprar o disponer del dominio.
2. Apuntar DNS al servidor.
3. Crear WordPress y HTTPS.
4. Instalar el plugin y tema reutilizables.
5. Crear un usuario o contraseña de aplicación.

MyDirectoryTool se encarga después de:

1. Crear el proyecto.
2. Verificar WordPress.
3. Obtener la configuración del plugin.
4. Guardar el mapeo de campos y taxonomías.
5. Probar medios, posts y borrado.
6. Configurar sector, contenido, territorio y cola.
7. Activar búsqueda y publicación.

Objetivo: menos de 15 minutos desde “WordPress preparado” hasta “directorio
listo para buscar negocios”.

### Versión posterior: aprovisionamiento del servidor

Si todos los sitios viven en un servidor controlado, una fase futura podrá:

- Crear el stack Docker de WordPress y MySQL.
- Crear volumen, base de datos y usuario.
- Generar virtual host de nginx.
- Solicitar certificado TLS.
- Instalar y activar plugin y tema.
- Crear credenciales REST.

Esta automatización necesita una capa de infraestructura privilegiada y no debe
mezclarse con el backend web normal. No es requisito para validar el producto
multidirectorio.

## 3. Estado actual que debe preservarse

MyDirectoryTool ya ofrece:

- Login privado.
- Búsqueda y caché de Google Places.
- Selección manual de negocios.
- Datos geográficos y de contacto estructurados.
- Reseñas, artículos, extractos y clasificación.
- Descarga y optimización de imágenes.
- Publicación WordPress y ACF.
- Cola persistente con pausa, reintentos y ritmo configurable.
- Eliminación completa desde el panel.
- Filtros por estado, texto y puntuación.
- Docker con un único puerto público para el frontend.

La transformación no debe reescribir todo. Debe extraer las decisiones específicas
de restaurantes y convertirlas en configuración por directorio.

## 4. Limitaciones que bloquean nuevos directorios

### Configuración global

Actualmente existen un único destino WordPress, credenciales globales y una
configuración de publicación común.

### Modelo específico

`place`, `tipo_de_comida`, los nombres ACF y el CPT `restaurante` están ligados
al primer caso de uso.

### Contenido específico

Prompts, secciones, títulos y clasificación están orientados a restauración.

### Cola única

Los trabajos no indican a qué directorio pertenecen ni qué credenciales deben
usar.

### Interfaz única

El panel no tiene selector de directorio, asistente de alta ni configuración.

### WordPress asumido

No existe todavía un contrato de capacidades para comprobar automáticamente
plugin, tema, CPT, taxonomías, ACF, imágenes y permisos.

## 5. Principios de transformación

### Compatibilidad primero

Dónde comer bien se registrará como el directorio inicial. Su comportamiento y
URLs no deben cambiar durante la migración.

### Configuración en lugar de condicionales

No se añadirán bloques como `if sector == peluqueria` repartidos por el código.
Los sectores se expresarán mediante plantillas, campos, taxonomías y reglas.

### Negocio separado del directorio

Un negocio representa una entidad real; su publicación en un directorio es una
relación independiente. Así una misma ficha puede participar en proyectos
distintos sin duplicar sus datos comunes.

### Conectores reemplazables

Google, OpenAI y WordPress deben estar detrás de servicios con contratos claros.
El núcleo no debe conocer detalles innecesarios de cada proveedor.

### Operación observable

Cada trabajo debe registrar directorio, negocio, fase, intentos, coste, tiempos y
error. Nunca debe existir una cola silenciosa compartida sin contexto.

### Seguridad por proyecto

Las credenciales se aíslan por directorio, se cifran en reposo y nunca se envían
al frontend ni aparecen en logs.

## 6. Arquitectura objetivo

```text
Frontend
├── selector de directorio
├── asistente de alta
├── búsqueda y moderación
├── configuración
└── salud y cola por proyecto

API
├── directories
├── businesses
├── discovery
├── content
├── publications
├── connectors
└── provisioning (futuro, aislado)

Servicios
├── Google Places connector
├── OpenAI/content connector
├── WordPress connector
├── media service
├── template engine
└── publication worker

Persistencia
├── directorios y configuración
├── negocios comunes
├── relación directorio-negocio
├── plantillas versionadas
├── trabajos y auditoría
└── secretos cifrados o secret store
```

## 7. Modelo de datos objetivo

### `directory`

```text
id
name
slug
sector_template_id
status: draft | testing | active | paused | archived
default_language
country_code
default_region
publication_interval_seconds
created_at
updated_at
```

### `directory_wordpress`

```text
directory_id
base_url
post_type
rest_base
plugin_version
theme_version
credential_reference
last_connection_test_at
last_connection_status
```

La contraseña de aplicación no debe guardarse en texto plano en esta tabla.

### `business`

Sustituye progresivamente a `place` como entidad compartida:

```text
id
google_place_id
name
address y geografía
contacto
rating
business_status
source_updated_at
created_at
updated_at
```

### `directory_business`

```text
directory_id
business_id
status: discovered | selected | queued | published | rejected | failed
category_data
wordpress_post_id
wordpress_url
published_at
created_at
updated_at
```

Clave única: `(directory_id, business_id)`.

### `sector_template`

```text
id
key: restaurants | hairdressers | workshops
name
business_label_singular
business_label_plural
default_post_type
required_fields
optional_fields
taxonomy_definitions
schema_type
content_template_id
version
```

### `content_template`

```text
id
sector_template_id
language
name
system_prompt
article_prompt
title_patterns
required_sections
excerpt_prompt
classification_prompt
version
status
```

Cada artículo debe registrar la versión utilizada.

### `field_mapping`

```text
directory_id
internal_field
wordpress_field
destination: acf | core | taxonomy
wordpress_type
required
enabled
```

Ejemplo restaurantes:

```text
phone       → telefono       → ACF
city        → municipio      → ACF
city        → municipio      → taxonomía
food_type   → tipo_de_comida → ACF
food_type   → tipo_comida    → taxonomía
```

Ejemplo peluquerías:

```text
phone       → telefono       → ACF
city        → municipio      → taxonomía
services    → servicios      → ACF/taxonomía
```

### `publication_job`

```text
id
directory_id
directory_business_id
job_type
status
attempts
max_attempts
scheduled_at
started_at
finished_at
last_error
idempotency_key
```

### `connector_event`

Registra llamadas externas sin secretos:

```text
directory_id
provider
operation
status
duration_ms
estimated_cost
error_code
created_at
```

## 8. Migración sin romper Dónde comer bien

### Paso 1: migraciones formales

Antes de añadir `directory_id`, introducir un sistema de migraciones versionadas
con copia previa y posibilidad de rollback probado.

### Paso 2: directorio por defecto

Crear automáticamente:

```text
name: Dónde comer bien
slug: dondecomerbien
sector: restaurants
wordpress: https://dondecomerbien.com
post type: restaurante
interval: 300 segundos
```

### Paso 3: añadir `directory_id`

Añadirlo inicialmente como nullable, rellenar todas las filas existentes con el
directorio por defecto y convertirlo después en obligatorio donde corresponda.

Tablas afectadas:

```text
search
search_result o relación equivalente
directory_business
blog_article
publication_queue
```

### Paso 4: compatibilidad temporal

Las variables `WP_URL`, `WP_USER` y `WP_APP_PASS` pueden seguir funcionando como
fallback únicamente para el directorio inicial durante la transición.

### Paso 5: extraer configuración

Mover progresivamente fuera del código:

- CPT y REST base.
- Mapeo ACF.
- etiquetas de interfaz.
- prompts y títulos.
- clasificador sectorial.
- ritmo de publicación.

### Paso 6: verificar equivalencia

Antes de crear otro directorio, Dónde comer bien debe poder buscar, guardar,
generar, publicar, borrar y operar su cola a través del nuevo modelo sin cambios
visibles.

## 9. Plantillas sectoriales

Una plantilla sectorial no es solo un prompt. Incluye:

- Nombre singular y plural.
- Icono y terminología del panel.
- Tipo Schema.org.
- Campos obligatorios y opcionales.
- Taxonomías.
- Prompts y secciones.
- Reglas de títulos.
- Validadores de calidad.
- Consultas de búsqueda sugeridas.
- Criterios para aceptar o rechazar resultados.

### Restaurantes

```text
schema: Restaurant
categoría: tipo de comida
secciones: cocina, ambiente, servicio, opiniones, contacto
validación: debe ser un establecimiento donde se sirve comida
```

### Peluquerías

```text
schema: HairSalon
categoría: servicios
secciones: servicios, especialidades, instalaciones, atención, contacto
validación: debe prestar servicios de peluquería o barbería
```

El validador sectorial debe actuar antes de guardar o encolar para reducir casos
como atracciones, parques o negocios con nombres ambiguos.

## 10. Contrato con WordPress

El plugin reutilizable debe exponer una comprobación de capacidades, por ejemplo:

```text
GET /wp-json/mydirectorytool/v1/capabilities
```

Respuesta conceptual:

```json
{
  "plugin_version": "1.0.0",
  "post_types": ["restaurante"],
  "taxonomies": ["municipio_restaurante", "provincia_restaurante"],
  "acf_available": true,
  "schema_enabled": true,
  "theme_compatible": true
}
```

El conector de MyDirectoryTool debe poder:

- Autenticar.
- Leer capacidades.
- Crear, consultar, actualizar y borrar una ficha de prueba.
- Subir y borrar una imagen de prueba.
- Validar campos requeridos.
- Asignar taxonomías.
- Verificar que la URL pública responde.

La prueba debe limpiar todo lo creado, incluso tras un fallo parcial.

## 11. Asistente de creación de directorio

### Pantalla 1: identidad

- Nombre.
- Slug interno.
- Sector o plantilla.
- Idioma.
- País y territorio inicial.

### Pantalla 2: WordPress

- URL HTTPS.
- Usuario.
- Contraseña de aplicación.
- Botón “Probar conexión”.

No se avanza si falla autenticación, REST o TLS.

### Pantalla 3: capacidades

- Plugin detectado y versión.
- Tema compatible.
- CPT disponible.
- ACF disponible.
- Taxonomías y campos encontrados.
- Avisos y correcciones necesarias.

### Pantalla 4: contenido

- Plantilla sectorial.
- Vista previa de secciones y títulos.
- Idioma y tono.
- Campos obligatorios.
- Imagen y galería.

### Pantalla 5: publicación

- Intervalo.
- Máximo de intentos.
- Publicación manual o automática.
- Límite diario opcional.
- Estado inicial pausado.

### Pantalla 6: prueba

1. Crear ficha temporal.
2. Subir imagen temporal.
3. Comprobar ACF/taxonomías.
4. Abrir URL pública.
5. Borrar ficha e imagen.
6. Mostrar informe.

### Pantalla 7: activación

Resumen, costes estimados, advertencias y botón “Crear directorio”. El directorio
empieza en estado `draft` o `paused`; nunca debe iniciar una publicación masiva
sin una acción explícita.

## 12. Cambios del frontend

### Navegación

```text
selector de directorio
├── resumen
├── negocios
├── búsquedas
├── cola
├── contenido
├── WordPress
└── configuración
```

### Dashboard global

- Directorios activos, pausados y con errores.
- Trabajos pendientes por proyecto.
- Último error y última publicación.
- Costes aproximados.
- Salud de conectores.

### Contexto visible

Toda pantalla debe mostrar claramente qué directorio está activo. Acciones
destructivas o masivas nunca deben depender de un contexto implícito.

## 13. Cambios del backend

### Eliminar configuración global del flujo

Los servicios recibirán un `directory_context` con destino, credenciales,
plantillas y mapeos. No leerán directamente un único `WP_URL` global.

### WordPress client por directorio

```text
WordPressClient(directory_id)
├── test_connection
├── capabilities
├── upload_media
├── create_business
├── update_business
├── delete_business
└── assign_terms
```

### Pipeline configurable

```text
selección
→ validación sectorial
→ enriquecimiento
→ contenido según plantilla/version
→ imágenes
→ mapeo de campos/taxonomías
→ publicación en destino
→ verificación
```

### Cola aislada

Cada trabajo contiene `directory_id`. Pausar un directorio no debe detener los
demás. Deben existir límites por proyecto y, posteriormente, límites globales.

## 14. Credenciales y seguridad

- No almacenar contraseñas de aplicación en texto plano.
- Usar cifrado con una clave maestra fuera de la base o un secret store.
- No devolver secretos al frontend después de guardarlos.
- Mostrar únicamente que una credencial existe y cuándo fue validada.
- Permitir rotación sin recrear el directorio.
- Separar credenciales de WordPress de credenciales de infraestructura.
- Registrar quién cambió una conexión y cuándo.
- Prohibir URLs no HTTPS salvo entornos locales explícitos.
- Evitar SSRF validando destinos y bloqueando redes no autorizadas según el modo.

## 15. Empaquetado reutilizable de WordPress

El repositorio debe incluir fuentes versionadas:

```text
wordpress/
├── plugins/mydirectorytool-core/
├── themes/mydirectorytool-directory-theme/
└── presets/
    ├── restaurants.json
    └── hairdressers.json
```

El tema base debe parametrizar:

- Nombre y logotipo.
- Colores y tipografía.
- Textos de portada.
- Etiqueta singular/plural.
- Taxonomía principal.
- Datos de contacto visibles.

No debe contener nombres como `restaurante` en componentes que sean realmente
comunes. Las diferencias sectoriales deben venir del preset/plugin.

## 16. Calidad y validación sectorial

Antes de guardar o encolar:

- Comprobar tipos/categorías devueltos por Google.
- Aplicar reglas positivas y negativas de la plantilla sectorial.
- Marcar resultados dudosos para revisión.
- Permitir rechazo permanente dentro de un directorio.
- Evitar que un elemento rechazado vuelva a añadirse automáticamente.

Estados recomendados:

```text
válido
dudoso
rechazado
```

La valoración numérica puede ayudar a moderar, pero no determina si un negocio
pertenece al sector.

## 17. Observabilidad y costes

Por directorio mostrar:

- Consultas y detalles de Google.
- Tokens o coste estimado de OpenAI.
- Imágenes descargadas/subidas.
- Trabajos completados y fallidos.
- Tiempo medio de publicación.
- Última conexión WordPress correcta.
- Cuota o límite diario configurado.

No se debe activar una automatización masiva sin estimación de volumen y coste.

## 18. Fases de implementación

### Fase A: estabilización

- Terminar y revisar Dónde comer bien.
- Añadir migraciones formales.
- Añadir pruebas del pipeline y del borrado.
- Añadir validación sectorial básica.

### Fase B: `directory` sin cambiar la interfaz

- Introducir repositorios y migraciones formales todavía sobre SQLite.
- Preparar y ensayar la migración a PostgreSQL según el runbook específico.
- Crear tablas multidirectorio.
- Migrar datos existentes al directorio por defecto.
- Introducir contexto de directorio en backend y cola.
- Mantener compatibilidad con variables actuales.

### Fase C: selector y configuración

- Selector de directorio.
- CRUD de proyectos.
- Configuración WordPress por directorio.
- Secretos cifrados.
- Estado y cola aislados.

### Fase D: plantillas sectoriales

- Extraer prompts y mapeos de restaurantes.
- Versionar plantilla `restaurants`.
- Crear plantilla `hairdressers`.
- Añadir validadores y campos sectoriales.

### Fase E: contrato WordPress

- Plugin reutilizable.
- Endpoint de capacidades.
- Tema configurable.
- Prueba automática con limpieza.

### Fase F: asistente

- Implementar las siete pantallas.
- Validaciones bloqueantes.
- Informe de prueba.
- Activación explícita.

### Fase G: segundo directorio piloto

- Instalar WordPress en un dominio de prueba.
- Crear directorio de peluquerías.
- Seleccionar un lote pequeño.
- Publicar tres fichas.
- Revisar taxonomías, diseño, Schema y borrado.
- Documentar todo lo específico que aún quede en código.

### Fase H: aprovisionamiento opcional

- Servicio aislado de infraestructura.
- Plantillas Docker/nginx/TLS.
- Auditoría y rollback.

## 19. Orden que no debe alterarse

```text
estabilizar
→ migraciones
→ directory por defecto
→ contexto por proyecto
→ plantillas configurables
→ plugin/tema reutilizables
→ pruebas de conexión
→ asistente
→ segundo directorio piloto
→ aprovisionamiento automático
```

No empezar por el asistente: si el núcleo todavía contiene supuestos de
restaurantes, el asistente solo esconderá una configuración frágil.

## 20. Criterios para lanzar el segundo directorio

- Dónde comer bien sigue funcionando sin regresiones.
- Cada tabla y trabajo relevante tiene `directory_id`.
- Credenciales separadas y cifradas.
- Cola pausable por proyecto.
- Prompts y mapeos fuera del código específico.
- Plugin y tema instalables desde fuentes versionadas.
- Prueba WordPress crea y limpia una ficha temporal.
- El asistente bloquea configuraciones incompletas.
- Existe plantilla sectorial para peluquerías.
- Se puede publicar y borrar una ficha sin afectar otro directorio.

## 21. Definición de terminado

La primera versión multidirectorio estará terminada cuando, partiendo de un
WordPress preparado, un operador pueda:

1. Crear un proyecto sin editar archivos `.env`.
2. Conectar WordPress y guardar credenciales con seguridad.
3. Superar una prueba automática completa.
4. Elegir una plantilla sectorial.
5. Buscar y seleccionar negocios del territorio.
6. Publicar tres fichas correctas.
7. Pausar, reintentar y borrar desde el panel.
8. Cambiar a Dónde comer bien y comprobar que sus datos/cola son independientes.

## 22. Riesgos principales

| Riesgo | Mitigación |
|---|---|
| Romper el directorio actual | Migración incremental y directorio por defecto |
| Mezclar publicaciones entre dominios | `directory_id` obligatorio e idempotencia por proyecto |
| Exponer credenciales | Cifrado, redacción de logs y backend exclusivo |
| Duplicar negocios | `business` común y restricción por directorio |
| Prompts genéricos de baja calidad | Plantillas versionadas y revisión por sector |
| WordPress mal preparado | Endpoint de capacidades y prueba bloqueante |
| Publicar negocios incorrectos | Validación sectorial y estado dudoso/rechazado |
| Costes inesperados | Límites, estimación y métricas por directorio |
| Automatización de servidor peligrosa | Servicio privilegiado separado y fase posterior |

## 23. Registro de avance

| Fase | Estado | Fecha | Commit | Notas |
|---|---|---|---|---|
| A. Estabilización | En curso | | | Dónde comer bien operativo |
| B. Núcleo multidirectorio | Pendiente | | | |
| C. Selector y configuración | Pendiente | | | |
| D. Plantillas sectoriales | Pendiente | | | |
| E. Contrato WordPress | Pendiente | | | |
| F. Asistente | Pendiente | | | |
| G. Directorio piloto | Pendiente | | | Peluquerías recomendado |
| H. Aprovisionamiento | Futuro | | | No bloquea la primera versión |

## 24. Próximo bloque de trabajo recomendado

No crear todavía el asistente visual. El siguiente bloque debe:

1. Introducir migraciones SQLite versionadas y backups automáticos previos.
2. Diseñar e implementar `directory` y `directory_wordpress`.
3. Crear Dónde comer bien como directorio por defecto.
4. Añadir `directory_id` a la cola mediante una migración segura.
5. Hacer que el estado de cola se consulte por directorio.
6. Mantener la interfaz actual apuntando implícitamente al directorio por defecto.
7. Probar que el comportamiento visible no cambia.

Solo después se añadirá el selector de directorio.

La migración de motor está detallada en
[Migración a PostgreSQL](postgresql-migration-plan.md) y no debe ejecutarse
mientras la publicación masiva actual siga en curso.

## 25. Dónde comer bien como implementación de referencia

El directorio de restaurantes es el piloto funcional, no una plantilla que deba
copiarse y editarse a mano para cada sector.

### Capacidades ya demostradas

- CPT estable en plugin.
- Taxonomías, backfill y REST.
- Tema con archivos, tarjetas, galerías y navegación.
- Canonical, Open Graph, Schema, sitemaps y política `noindex`.
- Imágenes, contacto, mapa y datos territoriales.
- Auditoría de calidad reproducible.
- Backups y rollback documentados.

### Elementos que siguen acoplados a restaurantes

| Implementación actual | Configuración futura |
|---|---|
| CPT `restaurante` | `directory.content_type` |
| Slug `restaurantes` | `directory.public_slug` |
| Schema `Restaurant` | `sector.schema_type` |
| `tipo_comida_restaurante` | `sector.primary_taxonomy` |
| Textos “restaurante” y “dónde comer” | etiquetas del perfil sectorial |
| Hero gastronómico | identidad y recursos del directorio |
| Prompts de comida | plantillas de contenido versionadas |
| ACF de restaurante | esquema de campos del sector |
| Intervalo de dos párrafos | configuración de presentación |
| Umbral SEO de tres fichas | política SEO del directorio |

### Regla para el segundo directorio

No se duplicarán tema y plugin cambiando palabras. Antes de peluquerías deberán:

1. Leer etiquetas, slugs, taxonomías y Schema desde un perfil.
2. Exponer capacidades y configuración desde el plugin.
3. Permitir que el tema consulte esas capacidades.
4. Mover textos y recursos visuales a configuración del directorio.
5. Hacer que MyDirectoryTool cree y valide el perfil.
6. Ejecutar el mismo auditor con el nuevo `post_type`.

El script `scripts/audit-wordpress-content.php` ya acepta el tipo de contenido
como argumento y constituye la primera herramienta operativa reutilizable entre
sectores.

`scripts/propose-wordpress-titles.py` añade una segunda pieza reutilizable:
combina el inventario de WordPress con la entidad de negocio, propone títulos y
comprueba longitud y duplicados. Su salida es un informe; la futura interfaz
multidirectorio deberá convertirlo en un flujo:

```text
Auditoría
→ propuestas
→ comparar título actual/nuevo
→ aprobar o rechazar
→ aplicar lote
→ conservar slug
→ registrar auditoría
```

La generación no debe tener permisos de escritura. La aplicación del lote será
una acción separada, autenticada y reversible.

## 26. Política de contenido e indexación reutilizable

Para cualquier sector:

- Las páginas de taxonomía son navegables desde el primer negocio.
- Una página con menos de tres fichas y sin descripción editorial usa `noindex`.
- Esas páginas se omiten del sitemap.
- Al alcanzar tres fichas o recibir una descripción útil, vuelven a ser
  indexables automáticamente.
- Las categorías prioritarias se eligen por inventario real.
- Los textos editoriales no deben inventar experiencia ni generar cientos de
  variaciones para buscadores.
- La portada enlaza las categorías con mayor utilidad.

El umbral debe convertirse en configuración antes del segundo directorio; el
valor inicial validado en restaurantes es `3`.
