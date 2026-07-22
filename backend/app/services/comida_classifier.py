from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config("OPENAI_API_KEY"))

def detectar_tipo_comida(texto: str) -> str:
    prompt = f"""
Extrae de forma breve el tipo de comida principal a partir de este texto. 
Devuelve solo una palabra o categoría clara como 'italiana', 'japonesa', 'mallorquina', 'mediterránea', 'hamburguesas', etc. 
No expliques nada más, solo responde con el tipo de comida.

Texto:
\"\"\"
{texto}
\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{ "role": "user", "content": prompt }],
        temperature=0.3,
    )
    
    return response.choices[0].message.content.strip().lower()
