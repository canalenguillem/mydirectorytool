# Fix: asteriscos de Markdown visibles en los extractos publicados

Fecha: 26 de julio de 2026.
Autor: sesión de Claude Code (en ausencia de Codex).

## Síntoma

El usuario reportó ver literalmente `**texto**` en los extractos de la
página de archivo (`dondecomerbien.com/restaurantes/`) en vez de negrita
renderizada.

## Causa

`generar_excerpt()` (`backend/app/services/openai_writer.py`) recibe como
entrada `data["content"]`: el cuerpo del artículo en **Markdown crudo**
(con `**negrita**` de sobra, tal como lo escribe `generar_articulo_blog`).
El modelo, al resumir un texto lleno de marcado, tiende a copiar ese mismo
estilo en su respuesta.

El contenido del post sí se convierte correctamente de Markdown a HTML
antes de publicarse (`markdown2.markdown(...)` en
`backend/app/services/wordpress.py:268`), pero el excerpt se envía tal
cual (`wordpress.py:301`, `"excerpt": data.get("excerpt", "")`) — sin
ninguna conversión. WordPress no interpreta Markdown en el excerpt, así
que el `**` queda literal en el HTML publicado.

## Cambio aplicado

`backend/app/services/openai_writer.py`:

1. **Prompt reforzado**: `generar_excerpt()` ahora pide explícitamente
   texto plano, sin negrita, cursiva, código ni almohadillas.
2. **Limpieza defensiva**: nueva función `_strip_markdown()`, aplicada
   siempre al resultado antes de devolverlo — quita `**negrita**`,
   `__negrita__`, `*cursiva*`, `` `código` `` y almohadillas de título,
   sin tocar asteriscos sueltos que no forman parte de un marcado (se
   probó explícitamente que no rompe texto normal con un `*` aislado).
   Es un cinturón de seguridad por si el prompt no basta — mismo patrón
   que ya se vio con la reclasificación de tipo de comida y la retórica
   de los artículos: una instrucción por sí sola no siempre es
   suficiente con este modelo.

## Verificación

- Regenerado el extracto de 2 fichas reales (sin tocar caché ni
  WordPress): 0/2 con `**` en el resultado.
- Casos de prueba unitarios de `_strip_markdown()`: negrita, cursiva,
  código y encabezado sueltos limpiados correctamente; un `*` aislado sin
  pareja se deja intacto (no genera falsos positivos).

## Limpieza retroactiva de lo ya publicado

Se detectaron **11 de 349** posts publicados con `**` visible en el
excerpt real de WordPress. Con confirmación del usuario, se limpiaron
in-place: se leyó el excerpt existente vía la API REST de WordPress
(`context=edit` para obtener el campo `raw`), se le aplicó la misma
`_strip_markdown()` (sin volver a llamar a OpenAI — cambio de formato
puro, no editorial, el texto no cambia) y se hizo `POST` del resultado a
cada post. Verificado después: 0/349 con `**` en el excerpt.

IDs de WordPress corregidos: 4947, 4925, 4914, 4903, 4004, 3982, 3623,
3063, 2823, 1903, 1188.

## Despliegue

`docker compose up -d --build backend`. Arranque limpio, sin errores.
