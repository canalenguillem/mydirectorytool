# Contenido y enlaces para taxonomías prioritarias

Fecha: 23 de julio de 2026.

## Criterio

Se priorizaron páginas con varios restaurantes y variedad suficiente. No se
generaron textos para todas las combinaciones ni páginas orientadas únicamente
a captar búsquedas.

La decisión sigue las recomendaciones de Google Search Central sobre contenido
útil para personas y navegación interna rastreable.

## Backup

`/home/guillem/backups/dondecomerbien/2026-07-23_pre_term_descriptions/`

Contiene un volcado verificado de `wp_terms` y `wp_term_taxonomy` inmediatamente
anterior a los cambios.

## Descripciones añadidas

Municipios:

- Cala Millor
- Palma
- Bergamo
- Sineu
- Alcúdia
- Port d’Alcúdia

Provincias:

- Illes Balears
- Bergamo

Tipos de comida:

- Mediterránea
- Mallorquina
- Italiana
- Española

Las introducciones explican qué puede hacer el usuario en cada página y qué
variedad ofrece el inventario. No contienen números que queden obsoletos ni
afirmaciones de experiencia personal inexistente.

## Portada

Tema `mydirectorytool-wp-theme`, commit `d8908a6`.

La portada incorpora:

- Ocho municipios con más restaurantes.
- Seis tipos de comida con más restaurantes.
- Conteo visible.
- Enlaces HTML rastreables.
- Actualización automática según el inventario.
- Tarjetas compartidas con el resto del directorio.

## Validación

- Cala Millor: HTTP 200, descripción visible, Open Graph y 12 tarjetas.
- Illes Balears: HTTP 200, descripción visible, Open Graph y 12 tarjetas.
- Mediterránea: HTTP 200, descripción visible, Open Graph y 12 tarjetas.
- Página 2 de Illes Balears: HTTP 200.
- Portada: HTTP 200 y navegación prioritaria presente.
- Sitemap de restaurantes: presente.
- Sitemap de municipios: presente.
- Sitemap de provincias: presente.
- Sitemap de tipos de comida: presente.
- `robots.txt`: anuncia el índice de sitemaps.
- Errores PHP: ninguno.
