"""Generación de artículos de resumen (roundups) que enlazan a varias
fichas ya publicadas -- ej. "10 restaurantes de Barcelona",
"beach clubs de la bahía de Alcúdia". Sector-agnóstico a propósito: no
menciona "restaurante"/"comida" en ningún sitio del código, solo en el
texto que el propio usuario aporta como tema, para que sirva igual con
peluquerías, hoteles, veterinarios... en el próximo nicho.

Reutiliza exactamente las mismas reglas anti-repetición que
openai_writer.generar_articulo_blog (mismo cliente, mismo modelo,
mismas fórmulas prohibidas), adaptadas a un artículo con un apartado por
negocio en vez de uno solo.
"""

import re

from app.services.openai_usage import record_openai_usage
from app.services.openai_writer import client


def generar_articulo_resumen(tema: str, lugares: list[dict]) -> str:
    """lugares: lista de dicts con name, city, rating, url, excerpt (el
    extracto ya publicado de cada ficha, se usa como base factual -- no se
    inventan datos que no estén ahí). Devuelve markdown con "# título",
    introducción, un "## Nombre" por lugar terminado en un enlace a su
    ficha, y un cierre."""
    listado = "\n".join(
        f"- {l['name']} ({l['city']}, valoración {l['rating']}/5): {l['excerpt']} Enlace: {l['url']}"
        for l in lugares
    )

    prompt = f"""
Escribe un artículo en español para un blog local sobre "{tema}", presentando estos {len(lugares)} negocios ya publicados en el sitio.

Datos reales a incluir (no inventes ninguno más, no cambies valoraciones, nombres ni URLs):
{listado}

Estructura pedida:
1. Un título atractivo en una línea, precedido por "# " (markdown), relacionado con "{tema}" pero no genérico ni con fórmulas trilladas tipo "Los mejores sitios para...".
2. Una introducción de 80-120 palabras sobre "{tema}" que dé contexto (zona, qué tienen en común, para quién es útil esta selección), sin frases genéricas tipo "si buscas..." ni relleno.
3. Un apartado por cada uno de los {len(lugares)} negocios, con su nombre como subtítulo "## Nombre", 50-80 palabras cada uno, usando el dato real dado (valoración, ubicación, extracto) pero con SU PROPIA frase de apertura distinta en cada uno -- prohibido repetir la misma estructura de frase en dos apartados seguidos, prohibido usar "no es X, sino Y", prohibido empezar dos apartados con la misma palabra. Termina cada apartado con un enlace markdown de una sola línea con el texto "Ver ficha completa de [nombre]" apuntando exactamente a la URL dada (no la cambies).
4. Un cierre de 50-80 palabras con una recomendación práctica (por ejemplo, cómo elegir entre ellos según el plan) -- no un resumen genérico.

Responde solo con el markdown del artículo, sin explicaciones adicionales ni bloques de código.
"""
    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    record_openai_usage(response, "roundup_article_generation", None)
    md_text = response.choices[0].message.content.strip()
    md_text = re.sub(r"^```(?:markdown)?\s*", "", md_text, flags=re.IGNORECASE)
    md_text = re.sub(r"\s*```$", "", md_text)
    return md_text


def insertar_imagenes(md_text: str, lugares: list[dict]) -> str:
    """Inserta la imagen destacada de cada negocio (ya subida a WordPress
    en su propia ficha, no se sube nada nuevo) justo debajo de su
    subtítulo "## Nombre". Si un lugar no tiene imagen conocida, su
    apartado se queda igual que antes -- no rompe nada."""
    by_name = {l["name"]: l.get("image_url", "") for l in lugares}
    output = []
    for line in md_text.splitlines():
        output.append(line)
        heading_match = re.match(r"^##\s+(.+)$", line.strip())
        if heading_match:
            image_url = by_name.get(heading_match.group(1).strip())
            if image_url:
                output.append("")
                output.append(f"![{heading_match.group(1).strip()}]({image_url})")
    return "\n".join(output)


def generar_excerpt_resumen(md_text: str) -> str:
    from app.services.openai_writer import generar_excerpt

    content_lines = md_text.splitlines()
    if content_lines and content_lines[0].startswith("# "):
        content_lines = content_lines[1:]
    return generar_excerpt("\n".join(content_lines))
