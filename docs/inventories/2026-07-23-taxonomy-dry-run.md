# Inventario en seco para taxonomías

Fecha: 23 de julio de 2026.

Este informe se generó leyendo los metadatos de los 248 restaurantes publicados.
No creó términos, no asignó taxonomías y no modificó WordPress.

## Cobertura

| Campo ACF | Con valor | Vacío | Valores únicos |
|---|---:|---:|---:|
| `municipio` | 197 | 51 | 67 |
| `ciudad` | 197 | 51 | 67 |
| `provincia` | 198 | 50 | 20 |
| `tipo_de_comida` | 248 | 0 | 42 |

En el inventario actual, `municipio` y `ciudad` tienen exactamente la misma
cobertura y distribución. El fallback de ciudad no recuperaría ninguna de las
51 fichas vacías.

## Estado de las taxonomías

La versión 0.2.0 del plugin registra:

| Taxonomía | Administración | REST | Archivo público | Términos |
|---|---|---|---|---:|
| `municipio_restaurante` | Sí | Sí | No | 0 |
| `provincia_restaurante` | Sí | Sí | No | 0 |
| `tipo_comida_restaurante` | Sí | Sí | No | 0 |

No se habilitarán archivos públicos hasta completar el backfill, elegir los
slugs públicos y disponer de plantillas adecuadas.

## Equivalencias territoriales seguras propuestas

Estas equivalencias deben conservar una única etiqueta canónica:

| Origen | Término propuesto |
|---|---|
| `Balearic Islands` | `Illes Balears` |
| `Vizcaya` | `Bizkaia` |
| `Provincia di Bergamo` | `Bergamo` |

No se transformarán automáticamente municipio, distrito o localidad en otra
entidad. Por ejemplo, `Port de Sóller`, `Sóller`, `Santa Ponça`, `Cala Millor` y
`Palma` deben conservarse como localidades distintas mientras no exista un
modelo territorial jerárquico revisado.

## Tipos de comida que requieren normalización

Equivalencias seguras propuestas:

| Origen | Término propuesto |
|---|---|
| `andaluzas` | `Andaluza` |
| `andaluza` | `Andaluza` |
| `carnes` | `Carne` |
| `carne` | `Carne` |

Tratamientos especiales:

- `mediterránea-italiana` debería asignar dos términos: `Mediterránea` e
  `Italiana`.
- `carnes a la brasa` debe conservarse como término propio; expresa una
  especialidad más concreta que `Carne`.
- Los restantes valores pueden normalizar inicialmente mayúsculas y espacios
  sin cambiar su significado: `mallorquina` → `Mallorquina`, `mediterránea` →
  `Mediterránea`, etc.

## Datos que no deben adivinarse

- Las 51 fichas sin municipio deben permanecer sin término hasta enriquecer sus
  datos de origen.
- Las 50 fichas sin provincia deben permanecer sin término.
- Localidades extranjeras como Bergamo, Orio al Serio, Azzano San Paolo,
  Florencio Varela y El Pueblito no se reclasificarán automáticamente.
- No se usarán distrito, región o país como sustitutos de municipio o provincia.

## Próxima ejecución

El backfill deberá:

1. Admitir modo `dry-run` sin escrituras.
2. Ser idempotente.
3. Crear términos mediante las funciones nativas de WordPress.
4. Aplicar las equivalencias anteriores desde una tabla explícita.
5. Permitir varios tipos de comida por restaurante.
6. Procesar primero una muestra de 10 fichas.
7. Registrar por `post_id` qué asignaría, omitiría o consideraría ambiguo.
