# Auditoría de calidad del contenido

Fecha: 26 de julio de 2026.

## Herramienta

`scripts/audit-wordpress-content.php`

Ejecución dentro del contenedor WordPress:

```bash
php audit-wordpress-content.php restaurante
```

## Contexto

Auditoría repetida tras drenarse por completo la cola de publicación (274
completados) y la cola de reparación (127 completados) y tras desplegar el
cambio de modelos de OpenAI (`docs/inventories/2026-07-24-openai-model-upgrade.md`).
Es la primera auditoría con el catálogo local en estado 100% completo (345/345
fichas publicadas, con artículo y con tipo de comida).

## Snapshot

Restaurantes publicados en el momento de la auditoría: 346.

| Señal | Resultado | Auditoría anterior (23 jul) |
|---|---:|---:|
| Sin imagen destacada | 0 | 0 |
| Sin galería | 3 | 23 |
| Sin contacto | 5 | 10 |
| Sin ubicación completa | 2 | 51 |
| Sin extracto | 0 | 0 |
| Extracto corto | 0 | 0 |
| Título de más de 70 caracteres | 96 | 75 |
| Contenido de menos de 300 palabras | 0 | 0 |
| Grupos de títulos exactamente duplicados | 0 | 0 |
| Grupos de extractos exactamente duplicados | 0 | — |

Mejora clara en galería, contacto y ubicación (efecto directo de la cola de
reparación). Los títulos largos suben ligeramente en número absoluto porque
hay más fichas publicadas (346 vs 249), no porque empeore la proporción.

## Reconciliación SQLite ↔ WordPress

- IDs de WordPress publicados: 346.
- `wp_post_id` guardados en SQLite: 345.
- Diferencia: **1 post huérfano — ID 44 ("Porrón: Un Viaje Gastronómico al
  Corazón de Illes Balears")**, existe en WordPress pero sin registro local
  correspondiente. Es el mismo huérfano ya inventariado en
  `docs/project-progress-summary.md` §18 — no es un caso nuevo.
- Ningún `wp_post_id` de SQLite falta en WordPress (cero fichas "fantasma"
  en el lado local).

## Pendiente (sin cambios respecto a auditorías previas)

- Los 96 títulos largos siguen sin tocarse en bloque — la hoja de ruta pide
  medir primero la muestra ya aplicada en Search Console antes de continuar.
- El post huérfano 44 requiere decisión manual (¿crear registro local o
  despublicar?), no se ha tocado en esta auditoría porque es de solo lectura.
