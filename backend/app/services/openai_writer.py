import hashlib
import re

from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config("OPENAI_API_KEY"))


TITLE_PATTERNS = (
    "{name}: guía honesta para comer bien en {locality}",
    "Qué pedir en {name} y por qué merece una visita",
    "{name}, una mesa con personalidad propia en {locality}",
    "Comer en {name}: lo que conviene saber antes de ir",
    "{name}: cocina, ambiente y opiniones sin rodeos",
    "Una comida en {name}: así es la experiencia",
    "{name} bajo la lupa: carta, servicio y ambiente",
    "Dónde comer en {locality}: una visita a {name}",
    "{name}: razones para reservar mesa en {locality}",
    "Así se come en {name}: una guía basada en sus clientes",
    "{name}, más allá de la carta: qué puedes esperar",
    "¿Vale la pena comer en {name}? Esto dicen sus clientes",
    "{name}: una parada gastronómica para recordar",
    "Antes de visitar {name}: platos, ambiente y consejos",
    "{name} en {locality}: una experiencia contada al detalle",
    "La experiencia {name}: del primer plato al último detalle",
    "{name}: dónde el ambiente también forma parte del menú",
    "Lo mejor de {name}, según quienes ya se han sentado a su mesa",
    "{name}: una propuesta gastronómica con sello propio",
    "Guía de {name}: qué encontrarás al sentarte a la mesa",
)


def generar_titulo_unico(info: dict) -> str:
    name = " ".join(str(info.get("name") or "Restaurante").split())
    locality = " ".join(str(info.get("locality") or "la zona").split())
    if "balear" in locality.lower():
        locality = "Mallorca"
    stable_key = str(info.get("place_id") or name)
    index = int(hashlib.sha256(stable_key.encode()).hexdigest()[:8], 16) % len(TITLE_PATTERNS)
    return TITLE_PATTERNS[index].format(name=name, locality=locality)


def aplicar_titulo(article: str, title: str) -> str:
    article = article.strip()
    article = re.sub(r"^```(?:markdown)?\s*", "", article, flags=re.IGNORECASE)
    article = re.sub(r"\s*```$", "", article)
    if re.search(r"^#\s+.+$", article, flags=re.MULTILINE):
        return re.sub(r"^#\s+.+$", f"# {title}", article, count=1, flags=re.MULTILINE)
    return f"# {title}\n\n{article}"

def generar_articulo_blog(info: dict, idioma: str = "es"):
    title = generar_titulo_unico(info)
    prompt = f"""
Eres un redactor profesional experto en SEO y redacción web. Escribe un artículo muy completo y extenso (mínimo **1200 palabras**) en {idioma} sobre el siguiente negocio gastronómico local.

Resuelve las principales intenciones de búsqueda teniendo en cuenta la población del restaurante 
 el artículo debe resolver las principales intenciones de búsqueda nom "donde comer bien en ..."
"los mejores restaurantes en ..."

📝 El artículo debe incluir detalles ricos y variados, anécdotas, contexto histórico o cultural si es relevante, y descripciones sensoriales. Usa párrafos desarrollados y evita repeticiones.

🎯 La primera línea debe ser exactamente este título, precedido por `# `:
{title}

No inventes otro título, no lo reformules y no envuelvas el artículo en bloques de código.
⛔️ Si el restaurante está en las Islas Baleares, especifica siempre la isla exacta (Mallorca, Menorca, Ibiza o Formentera), nunca “Islas Baleares” a secas.


🔍 El contenido debe estar completamente en **formato Markdown**, incluyendo:
- Título principal como `#`
- Subtítulos como `##` y `###`
- Llamadas a la acción con `**negrita**`
- Teléfono y web destacados en una sección final
- Listas con `-` o `*`
- Palabras clave, meta descripción y llamada a la acción en su propia sección final

📌 Estructura detallada esperada (todo en Markdown, sin escribir “Subtítulo:” ni “Título:”):

- `#` Título SEO creativo y original
- Párrafo introductorio natural, con contexto y personalidad
- `##` Tipo de comida: describe los platos principales, ingredientes destacados y técnica culinaria
- `##` Ambiente y ubicación: entorno, decoración, vistas o música ambiente
- `##` Atención y servicio: amabilidad, rapidez, trato con el cliente
- `##` Opiniones de clientes: resume reseñas reales usando frases diferentes y naturales
- `##` ¿Por qué deberías visitarlo?: un párrafo con tono emocional y de recomendación
- `##` Llamada a la acción final: motiva a reservar o visitar
- `---`
- 📞 **Para reservas, puedes llamar al** {info.get("phone", "número no disponible")}  
  🌐 **Web del establecimiento:** {info.get("website", "no disponible")}
- `---`
- `**META-DESCRIPCIÓN:**` Una frase atractiva de no más de 155 caracteres para buscadores  
- `**LLAMADA A LA ACCIÓN:**` Frase directa para motivar al lector  
- `**PALABRAS CLAVE:**` 3 términos separados por comas

ℹ️ Datos del negocio:
- Nombre: {info['name']}
- Dirección: {info['address']}
- Localidad: {info['locality']}
- Teléfono: {info.get("phone", "número no disponible")}
- Web: {info.get("website", "no disponible")}

🗣 Opiniones de clientes reales:
{info['text']}

No uses listas numeradas ni etiquetas HTML. Todo debe estar en formato Markdown limpio. Evita repetir frases entre artículos.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    return aplicar_titulo(response.choices[0].message.content, title)




def generar_excerpt(texto: str) -> str:
    prompt = f"""
Resume el siguiente texto en 1 o 2 frases claras, atractivas y naturales para ser usadas como extracto en un blog gastronómico:

\"\"\"
{texto}
\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()
