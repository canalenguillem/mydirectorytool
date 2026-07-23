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
