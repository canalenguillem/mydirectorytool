# Modelo de datos

## Entidades actuales

### `search`

Representa una consulta realizada, con texto y hash para reutilizar resultados sin volver a consumir Google.

### `search_result`

Resultado descubierto pero todavía no incorporado al directorio.

Campos relevantes:

- Identidad y valoración.
- Dirección y geografía estructurada.
- Coordenadas.
- Teléfono, web y futuros datos de correo.
- Estado operativo.

### `place`

Negocio seleccionado por el operador. Es la entidad central del MVP.

Además de los datos del resultado, contiene:

- Estado de publicación.
- ID y URL de WordPress.
- Tipo de comida.

### `review` y `review_text`

Guardan reseñas individuales y su texto consolidado para la generación editorial.

### `blog_article`

Relaciona un Place ID e idioma con el archivo Markdown generado.

### `place_image` y `place_featured_image`

Registran imágenes locales y la elegida como destacada.

### `publication_queue` y `publication_queue_control`

Almacenan trabajos, intentos, errores y configuración de ejecución.

## Geografía común

Los negocios nuevos pueden almacenar:

```text
formatted_address
country
country_code
region
province
municipality
city
district
postal_code
latitude
longitude
```

Esta estructura es transversal a cualquier sector y será la base de páginas territoriales y filtros.

## Contacto

```text
phone
website
email
email_source
```

`email_source` es obligatorio conceptualmente cuando se empiecen a obtener correos. Debe permitir distinguir datos proporcionados manualmente, publicados en la web oficial o procedentes de otra fuente autorizada.

## Modelo multidirectorio propuesto

### `directory`

```text
id
name
slug
sector
status
default_language
wordpress_url
wordpress_post_type
publication_interval
created_at
updated_at
```

Las credenciales no deben almacenarse sin cifrar en esta tabla.

### `business`

Evolución de `place`. Representa el negocio independientemente del directorio:

```text
id
google_place_id
name
contact fields
location fields
source
source_updated_at
```

### `directory_business`

Relación entre directorio y negocio:

```text
directory_id
business_id
status
category
wordpress_post_id
wordpress_url
published_at
```

Esta separación permite que el mismo negocio participe en más de un proyecto sin duplicar su ubicación y contacto.

### `content_template`

```text
directory_id
name
language
prompt
title_patterns
required_sections
version
```

Todo artículo debe guardar la versión de plantilla que lo generó.

### `field_mapping`

Mapea datos internos a ACF u otros CMS:

```text
directory_id
internal_field
external_field
external_type
enabled
```

Así se evita codificar `telefono`, `tipo_de_comida` o `latitud` directamente para todos los futuros sectores.

### `publication_job`

Evolución de la cola actual con `directory_id`, tipo de trabajo y payload:

```text
directory_id
business_id
job_type
status
attempts
scheduled_at
started_at
finished_at
last_error
```

## Reglas de integridad futuras

- `google_place_id` único por negocio.
- Un negocio solo puede estar una vez en un directorio.
- Una imagen local no debe registrarse dos veces.
- Una reseña debe tener una clave estable para evitar duplicados.
- Una publicación completada debe ser idempotente.
- Todo dato enriquecido debe guardar fuente y fecha de actualización.
