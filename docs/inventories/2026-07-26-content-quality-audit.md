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

### Investigación del post huérfano 44 (26 de julio, ampliación)

Datos obtenidos directamente de WordPress (solo lectura):

- `post_type`: `restaurante`, `post_status`: `publish`.
- `post_date`: 2025-04-06 — más de un año antes de esta sesión, muy anterior
  a la cola de reparación y a toda la actividad reciente documentada.
- Título: "Porrón: Un Viaje Gastronómico al Corazón de Illes Balears".
- Tiene campos ACF completos (teléfono `+34 971 55 10 47`, código postal,
  tipo de comida, imagen destacada) — es un artículo real y completo, no un
  borrador ni una entrada de prueba.
- WordPress no guarda el Google Place ID en ningún campo, así que no hay
  forma programática de volver a enlazarlo con una ficha local.
- Se revisó `place_deletion.py`: su flujo de borrado exige que exista antes
  la fila local (`WHERE place_id = ?`) y borra primero WordPress y luego lo
  local — un fallo a mitad de camino dejaría el patrón contrario (fila local
  viva, WordPress borrado), no el que tenemos. **La herramienta actual no
  pudo haber producido este huérfano.**
- El backup más antiguo disponible con `places.db`
  (`/home/guillem/backups/dondecomerbien/2026-07-23_pre_repair_queue/`, 23
  de julio 21:19h) ya no tiene la fila local de este negocio — el huérfano
  es anterior a ese backup y a todo lo documentado en esta sesión.

Con esto, el origen más probable es una pérdida de la fila local muy
anterior (posiblemente ligada a la reestructuración de directorios que
menciona `.gitignore` como "estructura antigua"), no algo causado por el
trabajo reciente.

### Resolución (26 de julio, misma sesión)

Antes de actuar se buscó por nombre "Porrón" en las tablas locales y
apareció algo clave: **sí existe una ficha local para este negocio**
(`place_id = ChIJ-4SF7aNJlhIRcykVpDSUIlY`, mismo teléfono
`+34 971 55 10 47`, Manacor, Illes Balears), pero apunta a un post
**distinto**: `wp_post_id = 4202`
(`porron-cocina-ambiente-y-opiniones-sin-rodeos`, publicado y correcto).

Es decir, el post 44 no era una ficha única en riesgo de perderse — era
**contenido duplicado real**: el mismo negocio se publicó dos veces en
WordPress bajo dos posts distintos (44 en abril de 2025, y más tarde 4202,
que es el que la app sigue gestionando hoy). El post 44 quedó huérfano
porque, en algún momento, la fila local original se perdió/recreó sin
conservar la referencia a `wp_post_id=44`, y una publicación posterior creó
un post nuevo (4202) en vez de actualizar el existente.

**Acción tomada:** se borró el post 44 de WordPress (incluida su imagen
destacada, media ID 45) usando `place_deletion._delete_wordpress(44)` —
la misma función que usa la app para borrados normales, aplicada
directamente porque este caso no tenía fila local con la que invocar el
flujo completo (`delete_place_completely` exige una fila local previa).
Verificado: post 44 borrado, post 4202 intacto y sirviendo con normalidad.

Reconciliación final tras el borrado: **348 posts en WordPress = 348
`wp_post_id` en SQLite**, sin huecos en ninguna dirección (la cifra subió
desde 346/345 porque la cola de publicación siguió procesando negocios
nuevos en segundo plano entre la auditoría y este cierre — no es un error).
