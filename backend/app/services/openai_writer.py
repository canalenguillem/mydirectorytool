import hashlib
import re

from openai import OpenAI
from decouple import config
from app.services.openai_usage import record_openai_usage

client = OpenAI(api_key=config("OPENAI_API_KEY"))


TITLE_PATTERNS = (
    # Plantillas originales (se retiró "Lo mejor de {name}, según quienes ya
    # se han sentado a su mesa": era la más repetida en la auditoría de
    # WordPress — 17 de 346 posts — así que sale del grupo para nuevos
    # artículos; los ya publicados con ese título no se tocan).
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
    "{name}: una propuesta gastronómica con sello propio",
    "Guía de {name}: qué encontrarás al sentarte a la mesa",
    # Plantillas nuevas (26 de julio de 2026) para reducir la repetición
    # site-wide: con 20 plantillas y 348+ fichas, cada una se repetía de
    # media 17 veces. Con este grupo ampliado (59 en total) baja a ~6.
    "{name}: lo que dicen quienes ya han comido en {locality}",
    "¿Dónde comer en {locality}? {name} tiene buenas razones",
    "{name}: platos, precios y primera impresión",
    "Probamos {name} en {locality}: esto es lo que encontramos",
    "{name}: ficha completa para decidir si vale la pena",
    "Comer bien en {locality} pasa por {name}",
    "{name}: la carta, el servicio y lo que opinan sus clientes",
    "¿Qué se puede pedir en {name}? Un repaso completo",
    "{name} en {locality}: puntos fuertes y detalles a tener en cuenta",
    "Ficha de {name}: cocina, trato y ambiente en {locality}",
    "{name}, un clásico de {locality}",
    "Reseña de {name}: platos, servicio y opinión de clientes",
    "{name}: por qué aparece en las recomendaciones de {locality}",
    "Todo sobre {name}: carta, horarios y opiniones",
    "{name} en {locality}: qué esperar antes de reservar",
    "¿Se come bien en {name}? Repasamos las opiniones",
    "{name}: el sitio del que hablan en {locality}",
    "Guía rápida de {name} para quien visita {locality}",
    "{name}: sabores, servicio y detalles que marcan la diferencia",
    "Descubre {name}, una opción a tener en cuenta en {locality}",
    "{name}: platos destacados según sus clientes",
    "En {locality}, {name} se ha ganado su reputación",
    "{name}: cocina y ambiente explicados con detalle",
    "¿Reservar en {name}? Esto es lo que deberías saber",
    "{name}: entre los favoritos de {locality}",
    "Conoce {name}: carta, ambiente y trato al cliente",
    "{name}, una parada recomendable en {locality}",
    "Opiniones sobre {name}: lo bueno y lo que más se repite",
    "{name}: un vistazo a su cocina y su servicio",
    "¿Por qué reservan mesa en {name}? Te lo contamos",
    "{name} y su propuesta gastronómica en {locality}",
    "Sabores de {locality}: la experiencia en {name}",
    "{name}: ambiente, carta y opiniones de primera mano",
    "Visitar {name} en {locality}: lo que hay que saber",
    "{name}: detrás de sus buenas valoraciones",
    "En {locality} se habla bien de {name}: estas son las razones",
    "{name}: carta, precios orientativos y experiencia real",
    "Un acercamiento a {name}, en pleno {locality}",
    "{name}: platos que recomienda su clientela",
    "¿Qué encontrarás en {name}? Cocina, trato y ambiente",
)


# Ángulos retóricos: fuerzan variedad de estructura y evitan que el modelo
# converja siempre en los mismos recursos (antítesis "no es X, sino Y",
# pares contrastados "hay X que... otros que...", cierres con anáfora
# "Porque..."). Selección determinista por place_id, igual que los
# títulos, con una sal distinta para que título y ángulo no queden
# correlacionados entre sí.
ARTICLE_ANGLES = (
    {
        "nombre": "opinion_directa",
        "instruccion": (
            "Abre el artículo citando o parafraseando de forma natural un "
            "detalle textual concreto de una opinión real (no una pregunta "
            "genérica sobre dónde comer bien). Cierra la sección "
            "\"¿Por qué deberías visitarlo?\" en 2-3 frases directas que "
            "digan para qué tipo de comensal encaja mejor el lugar."
        ),
    },
    {
        "nombre": "contexto_lugar",
        "instruccion": (
            "Abre situando el negocio en su calle, barrio o localidad "
            "concretos, describiendo el entorno antes de hablar de comida. "
            "Cierra la sección \"¿Por qué deberías visitarlo?\" con una "
            "recomendación práctica: para quién y en qué ocasión encaja "
            "mejor una visita."
        ),
    },
    {
        "nombre": "pregunta_practica",
        "instruccion": (
            "Abre respondiendo directamente a una pregunta muy concreta que "
            "alguien buscaría sobre este negocio (qué pedir, qué tipo de "
            "comida sirven, para qué ocasión encaja), sin usar la fórmula "
            "\"si estás buscando dónde comer bien en...\". Cierra la "
            "sección \"¿Por qué deberías visitarlo?\" con 2-3 razones "
            "concretas en una lista breve."
        ),
    },
    {
        "nombre": "escena_sensorial",
        "instruccion": (
            "Abre con una escena sensorial concreta basada en las reseñas "
            "(un plato llegando a la mesa, un aroma, un sonido del local), "
            "sin mencionar búsquedas de Google ni frases sobre \"dónde "
            "comer bien\". Cierra la sección \"¿Por qué deberías "
            "visitarlo?\" describiendo brevemente el tipo de visita ideal "
            "(una cena, un almuerzo rápido, un plan en grupo)."
        ),
    },
    {
        "nombre": "expectativa_realidad",
        "instruccion": (
            "Abre contrastando lo que alguien podría esperar de un lugar "
            "así con lo que realmente cuentan los clientes, buscando una "
            "forma de plantear ese contraste que NO sea la construcción "
            "\"no es X, sino Y\". Cierra la sección \"¿Por qué deberías "
            "visitarlo?\" con una frase concreta y personal sobre el tipo "
            "de experiencia que ofrece."
        ),
    },
    {
        "nombre": "dato_concreto",
        "instruccion": (
            "Abre con un dato o detalle muy concreto de las reseñas (un "
            "plato que se repite, una valoración específica, un aspecto "
            "que varios clientes mencionan) como gancho, sin frase de "
            "apertura genérica sobre dónde comer bien. Cierra la sección "
            "\"¿Por qué deberías visitarlo?\" con una recomendación directa "
            "en una sola frase clara."
        ),
    },
)


def seleccionar_angulo(info: dict) -> dict:
    stable_key = str(info.get("place_id") or info.get("name") or "Restaurante")
    index = int(hashlib.sha256((stable_key + "::angle").encode()).hexdigest()[:8], 16) % len(ARTICLE_ANGLES)
    return ARTICLE_ANGLES[index]


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
    angulo = seleccionar_angulo(info)
    prompt = f"""
Eres un redactor profesional experto en SEO y redacción web. Escribe un artículo muy completo y extenso (mínimo **1200 palabras**) en {idioma} sobre el siguiente negocio gastronómico local.

Resuelve las principales intenciones de búsqueda teniendo en cuenta la población del restaurante
 el artículo debe resolver las principales intenciones de búsqueda nom "donde comer bien en ..."
"los mejores restaurantes en ..."

📝 El artículo debe incluir detalles ricos y variados, anécdotas, contexto histórico o cultural si es relevante, y descripciones sensoriales. Usa párrafos desarrollados y evita repeticiones.

🎭 Enfoque retórico de este artículo (síguelo para la apertura y el cierre; no lo menciones explícitamente ni lo nombres en el texto):
{angulo['instruccion']}

⛔️ No uses estas fórmulas, aunque sean gramaticalmente correctas — están sobreusadas en artículos anteriores de este mismo sitio y un lector que compare varias fichas las nota enseguida:
- La construcción "No es/No estamos ante X, sino Y" (o variantes como "No da la impresión de ser X, sino que...").
- Pares contrastados como "Hay [algo] que..., y hay otros que..." usados como recurso retórico.
- Empezar frases de la sección "¿Por qué deberías visitarlo?" con "Porque..." repetido.
- Empezar el artículo con "Si estás buscando dónde comer bien en {info.get('locality', 'la zona')}...".

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
        model="gpt-5.4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    record_openai_usage(response, "article_generation", info.get("place_id"))
    return aplicar_titulo(response.choices[0].message.content, title)




def _strip_markdown(texto: str) -> str:
    """Quita marcado Markdown de un texto corto.

    WordPress no renderiza el excerpt como Markdown (solo el contenido del
    post pasa por markdown2 en wordpress.py), así que cualquier **negrita**
    que se cuele en el extracto aparece literal en el sitio publicado.
    """
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"__(.+?)__", r"\1", texto)
    texto = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", texto)
    texto = re.sub(r"`([^`]+)`", r"\1", texto)
    texto = re.sub(r"^#+\s*", "", texto, flags=re.MULTILINE)
    return texto.strip()


def generar_excerpt(texto: str, place_id: str | None = None) -> str:
    prompt = f"""
Resume el siguiente texto en 1 o 2 frases claras, atractivas y naturales para ser usadas como extracto en un blog gastronómico.

⚠️ Responde en texto plano, sin ningún formato Markdown: nada de **negrita**, *cursiva*, `código` ni almohadillas de título. Solo la frase, sin marcado de ningún tipo.

\"\"\"
{texto}
\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    record_openai_usage(response, "excerpt_generation", place_id)
    return _strip_markdown(response.choices[0].message.content.strip())
