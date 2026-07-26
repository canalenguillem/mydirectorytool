# Actualización de modelos de OpenAI

Fecha de implantación: 24 de julio de 2026.
Autor: sesión de Claude Code (en ausencia de Codex).

## Objetivo

`gpt-4o` y `gpt-4o-mini` ya no aparecen en el listado oficial de precios de
OpenAI (sustituidos por la familia `gpt-5.x`). Aunque ambos IDs seguían
respondiendo con `HTTP 200` en `GET /v1/models/{id}` en el momento del
cambio, mantenerlos era un riesgo evitable: si OpenAI completa la retirada
sin aviso, `article_generation`, `excerpt_generation` y
`food_type_classification` dejarían de funcionar en producción.

## Cambio aplicado

| Servicio | Función | Modelo anterior | Modelo nuevo |
| --- | --- | --- | --- |
| `backend/app/services/openai_writer.py` | `generar_articulo_blog` (`article_generation`) | `gpt-4o` | `gpt-5.4` |
| `backend/app/services/openai_writer.py` | `generar_excerpt` (`excerpt_generation`) | `gpt-4o-mini` | `gpt-5.4-nano` |
| `backend/app/services/comida_classifier.py` | `detectar_tipo_comida` (`food_type_classification`) | `gpt-4o-mini` | `gpt-5.4-nano` |

Criterio de sustitución: se mantiene la misma proporción que ya existía
(modelo intermedio para el artículo largo, donde la calidad importa más;
modelo más barato y rápido para extracto y clasificación, tareas cortas y de
alto volumen — una llamada por cada ficha guardada). `gpt-5.4-nano` es el
escalón más económico de la familia `gpt-5.4`, más barato que el antiguo
`gpt-4o-mini`.

## Verificación realizada antes del cambio

- `GET https://api.openai.com/v1/models/{id}` (llamada gratuita, sin coste de
  tokens) confirmó `HTTP 200` para `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`,
  `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-4o` y `gpt-4o-mini` con
  la clave de `backend/.env`. Todos los IDs nuevos existen y son accesibles
  con la cuenta actual.
- **No verificado todavía:** calidad real de salida con los prompts
  existentes (el prompt de `article_generation` es muy prescriptivo en
  estructura Markdown; el de `food_type_classification` exige una única
  palabra de categoría — los modelos "nano" a veces son menos fiables en
  tareas de categorización estricta que un modelo "mini").

## Despliegue

26 de julio de 2026: `docker compose up -d --build backend`. Confirmado dentro
del contenedor que el código desplegado usa `gpt-5.4` / `gpt-5.4-nano`
(`docker exec ai_maps-backend-1 grep model= ...`). El contenedor se había
reiniciado el 25 de julio (13:20) sin reconstruir la imagen, por lo que entre
el commit (24 jul) y el rebuild (26 jul) siguió generando contenido real con
`gpt-4o` / `gpt-4o-mini` — visible en `openai_usage` por el `model` devuelto
(`gpt-4o-2024-08-06`, `gpt-4o-mini-2024-07-18`) hasta el 25 de julio 10:26.
**Lección:** `restart: unless-stopped` no reconstruye la imagen; tras cambiar
código hace falta `--build` explícito o el cambio no llega a producción.

## Verificación de calidad — resultado (26 de julio de 2026)

Prueba con 3 fichas reales que ya tenían artículo publicado (Mama Muú
Steakhouse - Playa, Calècc, Restaurante chino La Gran Muralla). Ejecutado
dentro del contenedor llamando directamente a `generar_articulo_blog`,
`generar_excerpt` y `detectar_tipo_comida` con datos reales de
`get_or_create_review_info` — **sin** escribir en la caché de artículos
(`get_or_create_article`) ni tocar WordPress. Detalle en
`docs/inventories/2026-07-26-content-quality-audit.md` (auditoría WordPress
en paralelo).

- **Artículos (`gpt-5.4`):** los 3 salieron entre 2067 y 2175 palabras (muy
  por encima del mínimo de 1200 del prompt), con el título en `# ` exacto
  esperado y estructura Markdown coherente a simple vista. Coste medio
  observado: **~0,045 $/artículo** (827-1252 tokens de entrada, 2717-2878 de
  salida), aproximadamente la mitad del coste por token de `gpt-4o`.
- **Extractos (`gpt-5.4-nano`):** 3/3 en 1-2 frases naturales, sin desviarse
  del formato. Coste: ~0,0007 $/extracto (prácticamente gratis).
- **Clasificación (`gpt-5.4-nano`) — muestra ampliada a 11 fichas (26 de
  julio):** 8/11 coincidieron exactamente con la categoría ya guardada. Las
  3 que difirieron siguen todas el mismo patrón: una categoría específica se
  sustituye por una más genérica —
  `carnes` → `mediterránea` (Mama Muú Steakhouse),
  `gallega` → `española` (Taberna da Galera),
  `mallorquina` → `mediterránea` (Como en Casa).
  **`mediterránea` actúa como una especie de categoría por defecto** de
  `gpt-5.4-nano` cuando la reseña no señala con fuerza una cocina regional
  concreta — incluso desplazando `mallorquina`, que es uno de los propios
  ejemplos del prompt. No es necesariamente incorrecto (son subconjuntos
  razonables), pero es una diferencia de comportamiento sistemática frente
  al modelo anterior, no ruido aleatorio. **No se ha aplicado ningún cambio
  de clasificación en producción** a partir de estas pruebas. Si en algún
  momento se decide reclasificar en bloque, conviene o bien revisar caso a
  caso, o bien afinar el prompt para que priorice la cocina regional
  específica cuando la reseña la mencione explícitamente, antes de caer en
  `mediterránea` por defecto.
- Las 9 llamadas de esta prueba quedaron registradas en `openai_usage` con
  `model = gpt-5.4-2026-03-05` / `gpt-5.4-nano-2026-03-17` (versión fechada
  que devuelve la API), confirmando que el tracking sigue funcionando sin
  cambios con los modelos nuevos.

## Rollback

Si algo falla: revertir `gpt-5.4` → `gpt-4o` y `gpt-5.4-nano` → `gpt-4o-mini`
en los dos ficheros de arriba y volver a construir con
`docker compose up -d --build backend` (ambos IDs antiguos seguían activos a
fecha de este documento).

## Origen de los nombres de modelo

Los nombres de la nueva familia (`gpt-5.4`, `gpt-5.6-sol/terra/luna`, etc.) se
obtuvieron combinando búsqueda web y verificación directa contra la API — no
proceden de documentación oficial de OpenAI leída directamente (la página
`openai.com/api/pricing` devolvió 403). Si OpenAI publica nomenclatura
distinta más adelante, confiar en el propio dashboard de la cuenta por encima
de este documento.

## Alcance

Solo cambian los IDs de modelo pasados a `client.chat.completions.create`.
No se ha tocado ningún prompt, temperatura, ni el registro de uso en
`openai_usage.py`.
