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

## ⚠️ Pendiente — para quien retome esto (Codex u otra sesión)

1. Generar 5-10 artículos de prueba con `gpt-5.4` y comparar longitud,
   estructura y coherencia con artículos ya publicados generados por
   `gpt-4o`.
2. Revisar una muestra de clasificaciones de `detectar_tipo_comida` con
   `gpt-5.4-nano`: si la categoría devuelta es inconsistente o demasiado
   genérica, subir a `gpt-5.4-mini` solo en esa función.
3. Comparar coste real antes/después usando el panel de `GET
   /usage/summary` (`docs/inventories/2026-07-24-openai-token-usage.md`),
   que ya registra modelo y tokens por operación.
4. Si algo falla, el rollback es trivial: revertir `gpt-5.4` → `gpt-4o` y
   `gpt-5.4-nano` → `gpt-4o-mini` en los dos ficheros de arriba (ambos IDs
   antiguos seguían activos a fecha de este cambio).
5. Los nombres de la nueva familia (`gpt-5.4`, `gpt-5.6-sol/terra/luna`,
   etc.) se obtuvieron combinando búsqueda web y verificación directa contra
   la API — no proceden de documentación oficial de OpenAI leída
   directamente (la página `openai.com/api/pricing` devolvió 403). Si
   OpenAI publica nomenclatura distinta más adelante, confiar en el propio
   dashboard de la cuenta por encima de este documento.

## Alcance

Solo cambian los IDs de modelo pasados a `client.chat.completions.create`.
No se ha tocado ningún prompt, temperatura, ni el registro de uso en
`openai_usage.py`.
