# Cola automática de reparación

Fecha: 23 de julio de 2026.

## Objetivo

Evitar la revisión manual de todas las fichas marcadas como incompletas. La
cola es independiente de la publicación de restaurantes nuevos.

## Selección

Al iniciar el primer lote se detectaron 92 fichas:

- 59 marcadas como publicadas;
- 33 todavía pendientes de publicación.

Una ficha entra si le falta contacto, ubicación completa, imágenes locales,
tipo de comida o el enlace a su artículo de WordPress.

## Comportamiento

Cada trabajo inspecciona sus carencias y ejecuta solo los pasos necesarios:

1. completa contacto y geografía mediante una petición de detalles a Google;
2. recupera el tipo de comida desde el artículo disponible;
3. descarga y registra imágenes si no existen localmente;
4. sincroniza ACF si el post sigue publicado;
5. regenera o recupera el artículo y vuelve a publicar solo si el post fue
   eliminado.

La cola usa SQLite, es persistente y dispone de:

- intervalo predeterminado de cinco minutos;
- máximo de tres intentos;
- pausa y reanudación;
- recuperación después de reiniciar Docker;
- estado actual y últimos errores;
- reintento de fallos.

Los datos que Google no proporcione no se inventan.

## Puesta en marcha

- Backup previo:
  `/home/guillem/backups/dondecomerbien/2026-07-23_pre_repair_queue/places.db`.
- SHA-256:
  `5e118dbd5ca9428b07bd7b516a6810be16881d484920e5193ebd4fd4756008e4`.
- Lote iniciado: 92 fichas.
- Duración inicial estimada: 7 horas y 40 minutos.

## Validación

La primera referencia antigua, `Ca'n Pintxo Restaurant`, conservaba una ruta
Markdown anterior al volumen Docker. La cola se corrigió para recuperar o
regenerar ese artículo antes de republicarlo.

Resultado del reintento:

- trabajo completado;
- nuevo post de WordPress: ID 3775;
- nueva URL guardada en SQLite;
- página pública verificada con HTTP 200;
- 91 trabajos permanecieron pendientes y la cola continuó activa.

## Población y taxonomías tras enriquecer

La ficha de Cafeteria PICNIC demostró que ACF ya contenía `Sa Coma`, aunque la
plantilla solo mostraba el código postal y la taxonomía municipal seguía vacía.

Correcciones:

- tema 1.5 muestra `población · código postal` en los datos de la ficha;
- plugin 0.5.2 sincroniza municipio, provincia y tipo después de guardar ACF;
- PICNIC quedó asignado a `Sa Coma` e `Illes Balears`;
- página pública validada con HTTP 200 y `Sa Coma · 07560`.

Repositorios:

- tema, commit `2dd9d91`;
- plugin, commit `3ee1cf7`.

## Cierre del 24 de julio de 2026

- Cola original: 92 trabajos.
- Completados: 92.
- Errores definitivos: 0.
- Porrón se republicó como post 4202.
- Kimbo Caffè se republicó como post 4213.
- WordPress quedó con 315 restaurantes publicados.

Los dos últimos fallos procedían de rutas de imágenes históricas registradas en
SQLite cuyos archivos ya no existían dentro del volumen Docker. Se corrigió el
detector para contar únicamente archivos físicos y la reparación valida siempre
la destacada antes de republicar.

Auditoría pública final:

| Señal | Resultado |
|---|---:|
| Sin destacada | 0 |
| Sin galería | 23 |
| Sin contacto | 11 |
| Sin ubicación completa | 4 |
| Sin extracto | 0 |
| Títulos de más de 70 caracteres | 80 |
| Contenido de menos de 300 palabras | 0 |

El panel detecta además 70 fichas sin copia local válida de sus imágenes. No
equivale a 70 galerías públicas ausentes: WordPress solo presenta 23 sin
galería. Deben tratarse como dos problemas distintos para evitar descargas
innecesarias.

### Sincronización de Sa Frontera

Sa Frontera conservaba diez filas antiguas con rutas inexistentes y diez fotos
nuevas válidas en `/data`, pero WordPress solo tenía una destacada y
`place_gallery` estaba vacío.

Se añadió sincronización para posts existentes:

- valida archivos físicos;
- asigna una destacada válida;
- reutiliza adjuntos existentes;
- sube únicamente los medios que falten;
- asocia los adjuntos al post;
- actualiza `place_gallery`.

Resultado:

- 10 imágenes locales disponibles;
- 1 destacada;
- 9 imágenes de galería subidas;
- 5 parejas renderizadas dentro del artículo;
- HTTP 200;
- artículo conservado sin republicar.
