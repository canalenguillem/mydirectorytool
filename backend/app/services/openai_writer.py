from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config("OPENAI_API_KEY"))

def generar_articulo_blog(info: dict, idioma: str = "es"):
    prompt = f"""
Eres un redactor profesional experto en SEO y redacción web. Escribe un artículo muy completo y extenso (mínimo **1200 palabras**) en {idioma} sobre el siguiente negocio gastronómico local.

Resuelve las principales intenciones de búsqueda teniendo en cuenta la población del restaurante 
 el artículo debe resolver las principales intenciones de búsqueda nom "donde comer bien en ..."
"los mejores restaurantes en ..."

📝 El artículo debe incluir detalles ricos y variados, anécdotas, contexto histórico o cultural si es relevante, y descripciones sensoriales. Usa párrafos desarrollados y evita repeticiones.

🎯 El título debe ser **único, atractivo y original**. Varía la estructura del título en cada artículo usando distintos enfoques:
- Pregunta directa: “¿Por qué todo el mundo habla de [Nombre]?”
- Afirmación de contraste: “[Nombre]: cocina de mercado sin pretensiones en [Localidad]”
- Número o dato: “5 razones para cenar en [Nombre] esta semana”
- Nombre propio como protagonista: “[Nombre], el refugio mallorquín que no sale en las guías”
- Imperativo: “Come en [Nombre] antes de que lo descubra todo el mundo”
- Descripción sensorial: “Paella con vistas al mar y sin trampa: así es [Nombre]”

⛔️ PROHIBIDO en el título: “Los Sabores de”, “Sabores Auténticos”, “Descubre”, “Oasis”, “Paraíso gastronómico”, “Viaje gastronómico”, “Un Rincón”, “La Magia de”, “Un Bocado de”.
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
    return response.choices[0].message.content




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
