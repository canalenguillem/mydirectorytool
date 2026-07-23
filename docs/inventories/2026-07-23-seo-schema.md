# SEO y Schema del directorio

Fecha: 23 de julio de 2026.

Plugin `mydirectorytool-core` versión 0.5.0, commit `8112706`.

## Metadatos

Las vistas del directorio generan:

- Canonical para archivo general, taxonomías y páginas paginadas.
- `og:type`, `og:title`, `og:description`, `og:url` y `og:site_name`.
- `og:image` cuando existe imagen destacada.
- Twitter Card, título, descripción e imagen cuando existe.

WordPress ya genera canonical para contenidos individuales. El plugin no añade
otro y evita duplicados.

Si en el futuro se activa Yoast, Rank Math, All in One SEO, SEOPress o The SEO
Framework, la capa social propia se desactiva para no duplicar etiquetas.

## JSON-LD Restaurant

Las fichas generan un objeto `Restaurant` con los campos disponibles:

- `name`
- `url`
- `image`
- `telephone`
- `email`
- `sameAs`
- `address`
- `geo`
- `servesCuisine`

Los valores vacíos se omiten. No se crean coordenadas, direcciones ni contactos
ficticios.

## Validación

Casos comprobados:

- Ficha Burdo: canonical único, seis etiquetas Open Graph, cuatro etiquetas
  Twitter y un JSON-LD `Restaurant` válido.
- Municipio Sóller: canonical único y metadatos sociales.
- Archivo de restaurantes: canonical único y metadatos sociales.
- Página 2 de Illes Balears: canonical específico de la página 2.
- Ficha Divný Janko sin galería ni coordenadas: HTTP 200, sin galería vacía, sin
  mapa vacío y Schema válido sin `geo`.

Todas las vistas respondieron HTTP 200 y no aparecieron errores PHP en logs.
