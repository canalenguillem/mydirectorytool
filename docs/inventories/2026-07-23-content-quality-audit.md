# Auditoría de calidad del contenido

Fecha: 23 de julio de 2026.

## Herramienta

`scripts/audit-wordpress-content.php`

Ejecución dentro del contenedor WordPress:

```bash
php audit-wordpress-content.php restaurante
```

El script es de solo lectura y acepta cualquier `post_type`. Audita:

- títulos;
- extractos;
- longitud de contenido;
- imagen destacada y galería;
- contacto y ubicación;
- patrones repetidos de títulos;
- duplicados exactos;
- taxonomías con una o dos fichas.

## Snapshot

Restaurantes publicados en el momento de la auditoría: 249.

| Señal | Resultado |
|---|---:|
| Sin imagen destacada | 0 |
| Sin galería | 23 |
| Sin contacto | 10 |
| Sin ubicación completa | 51 |
| Sin extracto | 0 |
| Extracto corto | 0 |
| Título de más de 70 caracteres | 75 |
| Contenido de menos de 300 palabras | 0 |
| Grupos de títulos exactamente duplicados | 0 |
| Grupos de extractos exactamente duplicados | 0 |
| Fichas con alguna alerta | 114 |

## Patrones de títulos detectados

| Patrón | Fichas |
|---|---:|
| “Lo mejor de…, según quienes…” | 6 |
| “¿Por qué todo el mundo habla de…?” | 5 |
| “Paella con vistas… sin trampa” | 9 |
| “Una propuesta gastronómica con sello propio” | 6 |
| “Una parada gastronómica para recordar” | 9 |
| “Lo que conviene saber antes de ir” | 9 |
| “Una experiencia contada al detalle” | 7 |

No son duplicados exactos, pero 51 fichas se concentran en siete fórmulas. La
siguiente mejora debe diversificar títulos sin modificar los slugs publicados.

## Páginas de taxonomía débiles

Antes de aplicar la política:

| Taxonomía | Una ficha | Dos fichas | Total débil |
|---|---:|---:|---:|
| Municipio | 45 | 9 | 54 |
| Provincia | 10 | 0 | 10 |
| Tipo de comida | 23 | 7 | 30 |
| Total | 78 | 16 | 94 |

## Política aplicada

Plugin `mydirectorytool-core` 0.5.1, commit `1b1fc03`.

- Menos de tres fichas y sin descripción: `noindex, follow`.
- La página sigue accesible desde la navegación.
- Se elimina de los sitemaps de taxonomía.
- Tres o más fichas, o descripción editorial: indexable.
- La decisión se recalcula automáticamente al cambiar el inventario.

Validación:

- Benicàssim, con una ficha: HTTP 200 y `noindex`.
- Cala Millor, con inventario suficiente: HTTP 200 e indexable.
- Sitemap de municipios: 13 URLs.
- Sitemap de provincias: 8 URLs.
- Sitemap de tipos de comida: 9 URLs.
- XML sin entradas vacías.

## Próximas correcciones

1. Crear un modo de propuesta de títulos, nunca una reescritura automática.
2. Priorizar los 75 títulos largos según impresiones y localidad.
3. Recuperar galerías de las 23 fichas que carecen de ellas cuando la fuente lo
   permita.
4. Enriquecer contacto y geografía sin inventar información.
5. Repetir la auditoría después de cada lote.
