# Variedad de títulos y retórica en artículos generados

Fecha: 26 de julio de 2026.
Autor: sesión de Claude Code (en ausencia de Codex).

## Objetivo

Tras revisar los primeros artículos reales generados con `gpt-5.4`
(`docs/inventories/2026-07-24-openai-model-upgrade.md`), aparecieron dos
problemas de repetición, uno ya conocido y otro nuevo:

1. **Títulos.** `generar_titulo_unico()` en `backend/app/services/openai_writer.py`
   elegía de forma determinista (hash de `place_id`) entre solo 20
   plantillas fijas. Con 348+ fichas publicadas, cada plantilla se repetía
   de media 17 veces — confirmado por la auditoría de WordPress
   (`docs/inventories/2026-07-26-content-quality-audit.md`), que ya
   contaba coincidencias de 17, 16, 15, 12, 9, 9 y 5 apariciones por
   patrón.
2. **Retórica del cuerpo del artículo (nuevo, específico de `gpt-5.4`).**
   Los 3 primeros artículos reales compartían casi palabra por palabra la
   misma estructura: apertura "Si estás buscando dónde comer bien en
   X...", la antítesis "No es/No estamos ante X, sino Y" en los tres, el
   recurso "Hay X que..., y hay otros que..." repetido varias veces por
   artículo, y el cierre "¿Por qué deberías visitarlo?" con anáfora
   "Porque..." en los tres. El prompt ya pedía "evita repeticiones" de
   forma genérica — evidentemente no bastaba: es el mismo patrón que ya
   vimos con la clasificación de tipo de comida convergiendo en
   "mediterránea" por defecto (`docs/inventories/2026-07-24-openai-model-upgrade.md`).

## Cambio aplicado

Ambos en `backend/app/services/openai_writer.py`:

### 1. Títulos: de 20 a 59 plantillas

Se retiró la plantilla más repetida ("Lo mejor de {name}, según quienes ya
se han sentado a su mesa", 17/346) y se añadieron 40 plantillas nuevas.
Mismo mecanismo de siempre (hash de `place_id` % número de plantillas,
determinista) — solo cambia el tamaño del grupo. Con 59 plantillas la
repetición media baja de ~17 a ~6 por plantilla en todo el catálogo.

No se ha tocado ningún título ya publicado en WordPress — eso sigue el
flujo separado y manual descrito en `docs/content-and-seo.md` ("Política
de títulos"). Este cambio solo afecta a artículos generados a partir de
ahora.

### 2. Retórica: ángulos deterministas + lista explícita de fórmulas prohibidas

Nueva estructura `ARTICLE_ANGLES`: 6 ángulos con instrucciones concretas
de apertura y cierre (`opinion_directa`, `contexto_lugar`,
`pregunta_practica`, `escena_sensorial`, `expectativa_realidad`,
`dato_concreto`). `seleccionar_angulo(info)` elige uno de forma
determinista por `place_id`, con una sal distinta a la de los títulos
(`"::angle"`) para que título y ángulo no queden correlacionados.

Además, el prompt ahora prohíbe explícitamente, citándolas de forma
literal, las fórmulas detectadas como sobreusadas: la antítesis "no es
X, sino Y", los pares contrastados "hay X que... otros que...", la
anáfora "Porque..." en el cierre, y la apertura "si estás buscando dónde
comer bien en...". Se optó por prohibir literalmente en vez de pedir
"más variedad" en abstracto, porque una instrucción genérica ya existía
en el prompt anterior y no impidió la convergencia — un patrón ya
documentado con este modelo (ver el hallazgo de reclasificación por
defecto a "mediterránea" en el inventario del 24 de julio).

## Verificación realizada

5 artículos generados con datos reales (llamando directamente a
`generar_articulo_blog` vía `get_or_create_review_info`, sin escribir en
la caché de `blog_article` ni publicar en WordPress — mismo método no
invasivo usado en verificaciones anteriores):

| Ficha | Ángulo | Título elegido | Palabras | "Porque" en cierre | Fórmulas prohibidas |
|---|---|---|---:|---:|---|
| La Taberna del Arriero | contexto_lugar | Comer en X: lo que conviene saber antes de ir | 2.161 | 0 | Ninguna |
| Hisupo (Valladolid) | contexto_lugar | Visitar X en Valladolid: lo que hay que saber | 1.890 | 0 | Ninguna |
| Pizzeria Roma Cala Millor | dato_concreto | X: una propuesta gastronómica con sello propio | 2.046 | 0 | Ninguna |
| La Terrazita Restaurante | expectativa_realidad | X: guía honesta para comer bien en Navalmoral de la Mata | 2.154 | 0 | Ninguna |
| Ca'n Nadal Restaurant | dato_concreto | Reseña de X: platos, servicio y opinión de clientes | 2.336 | 0 | Ninguna |

- 5 títulos distintos, ninguno coincide entre sí ni con los más repetidos
  históricamente.
- 0/5 usó la anáfora "Porque..." en el cierre (antes, 3/3 en la muestra
  original la usaban).
- 0/5 usó ninguna de las fórmulas prohibidas.
- Los dos artículos con el mismo ángulo (`contexto_lugar`,
  `dato_concreto` x2) muestran aperturas distintas entre sí pese a
  compartir estructura — el ángulo fija el recurso retórico, no el
  contenido.
- Longitud (1.890-2.336 palabras) en línea con las pruebas anteriores —
  no ha bajado la calidad ni el detalle.
- Simulación con 348 `place_id` ficticios: reparto de ángulos razonablemente
  equilibrado (51-67 por ángulo sobre 6), reparto de títulos con media 5,9
  repeticiones y máximo 13 (antes: media 17,4).

## Despliegue

Antes de la verificación, el fichero se copió directamente al contenedor
en marcha (`docker cp`) para poder probar con datos reales sin esperar a
un rebuild — la cola de publicación ya generaba con el prompt nuevo desde
ese momento, pero como parche en caliente, no durable (se habría perdido
en el próximo `docker compose up --build` sin commitear antes). Este
commit fija el cambio en el repositorio y el siguiente
`docker compose up -d --build backend` lo hace permanente.

## Pendiente

- No se han retocado los artículos ya publicados (fuera de alcance,
  igual que los títulos ya publicados).
- Con 59 plantillas de título y 6 ángulos, la repetición baja mucho pero
  no desaparece del todo (348 fichas ÷ 59 plantillas sigue dando algunas
  coincidencias). Si el catálogo sigue creciendo de forma significativa,
  valorar ampliar de nuevo el grupo de plantillas o mover a títulos
  parcialmente generados por IA con reglas de deduplicación — no hecho
  ahora porque el histórico (`docs/inventories/2026-07-23-title-proposals.md`)
  muestra que los títulos 100% libres por IA fueron precisamente el
  problema que motivó pasar a plantillas fijas.
