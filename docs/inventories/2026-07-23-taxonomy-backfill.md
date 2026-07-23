# Backfill de taxonomías

Fecha: 23 de julio de 2026.

## Punto de recuperación

Backup SQL inmediatamente anterior:

`/home/guillem/backups/dondecomerbien/2026-07-23_pre_taxonomy_sample/`

El volcado finalizó correctamente y su firma SHA-256 fue verificada.

## Implementación

Plugin `mydirectorytool-core` versión 0.3.0, commit `649c177`.

El motor:

- Lee `municipio`, con fallback a `ciudad`.
- Lee y normaliza `provincia`.
- Lee y normaliza `tipo_de_comida`.
- Omite valores vacíos.
- Permite varios tipos de comida.
- Procesa por `limit` y `offset`.
- Admite `dry-run`.
- Reemplaza la asignación gestionada para que los resultados sean repetibles.
- No se ejecuta automáticamente.

## Normalizaciones aplicadas

Provincia:

- `Balearic Islands` → `Illes Balears`
- `Vizcaya` → `Bizkaia`
- `Provincia di Bergamo` → `Bergamo`

Tipo de comida:

- `andaluza` y `andaluzas` → `Andaluza`
- `carne` y `carnes` → `Carne`
- `mediterránea-italiana` → `Mediterránea` + `Italiana`
- Los demás valores reciben una etiqueta inicial en mayúscula sin cambiar su
  significado.

## Pruebas por muestras

Primera muestra:

- 10 fichas procesadas.
- 10 modificadas.
- 0 errores.
- Los campos territoriales vacíos fueron omitidos.
- Segunda pasada: 0 cambios y 10 sin cambios.

Muestra territorial:

- 10 fichas procesadas.
- 10 modificadas.
- 0 errores.
- Incluyó Sóller, Platja de Muro, Cala Millor e Illes Balears.
- Segunda pasada: 0 cambios y 10 sin cambios.

## Resultado completo

| Taxonomía | Términos | Asignaciones |
|---|---:|---:|
| Municipio | 67 | 197 |
| Provincia | 18 | 198 |
| Tipo de comida | 39 | 249 |

Las 51 fichas sin municipio y las 50 sin provincia quedaron sin término, como
estaba previsto. Todas las fichas tienen tipo de comida; una de ellas tiene dos
términos.

## Prueba de idempotencia

Tras completar los lotes se ejecutó nuevamente todo el conjunto en modo
`dry-run`:

```text
procesadas: 248
cambios propuestos: 0
sin cambios: 248
errores: 0
```

## Validación final

- Restaurantes publicados: 248.
- Campos de las tres taxonomías presentes en REST.
- Portada: HTTP 200.
- Archivo de restaurantes: HTTP 200.
- Ficha de muestra: HTTP 200.
- Endpoint REST: HTTP 200.
- Errores PHP en logs: ninguno.
- Archivos públicos de las taxonomías: todavía desactivados.
