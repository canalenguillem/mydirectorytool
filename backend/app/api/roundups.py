import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.database import get_all_images_for_place, get_places_by_ids
from app.services.roundup_writer import generar_articulo_resumen, generar_excerpt_resumen
from app.services.wordpress import (
    crear_post_generico,
    markdown_a_html_restaurante,
    obtener_post_publicado,
    upload_media,
)

router = APIRouter()


class RoundupRequest(BaseModel):
    tema: str
    place_ids: list[str]


@router.post("/generate")
def generate_roundup(data: RoundupRequest):
    if len(data.place_ids) < 2:
        raise HTTPException(status_code=400, detail="Selecciona al menos 2 fichas")

    places = get_places_by_ids(data.place_ids)
    if len(places) != len(data.place_ids):
        raise HTTPException(status_code=404, detail="Alguna de las fichas seleccionadas ya no existe")

    lugares = []
    for place in places:
        if not place["publicado_en_wp"] or not place["wp_post_id"]:
            raise HTTPException(status_code=400, detail=f"{place['name']} todavía no está publicada")
        published = obtener_post_publicado(int(place["wp_post_id"]))
        if not published:
            raise HTTPException(
                status_code=502, detail=f"No se pudo leer la ficha publicada de {place['name']}"
            )
        lugares.append(
            {
                "name": place["name"],
                "city": place["city"] or place["municipality"] or "",
                "rating": place["rating"],
                "url": published["link"],
                "excerpt": published["excerpt"] or published["title"],
            }
        )

    md_text = generar_articulo_resumen(data.tema, lugares)
    title_match = re.search(r"^# (.+)", md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else data.tema
    html_content = markdown_a_html_restaurante(md_text)
    excerpt = generar_excerpt_resumen(md_text)

    # Imagen destacada: la primera imagen local disponible de la ficha
    # mejor valorada de la selección -- sin pedirle al usuario que elija.
    featured_media_id = None
    best_place = max(places, key=lambda p: p["rating"] or 0)
    images = get_all_images_for_place(best_place["place_id"])
    if images:
        featured_media_id = upload_media(images[0])

    result = crear_post_generico(title, html_content, excerpt, featured_media_id)
    if not result:
        raise HTTPException(status_code=502, detail="No se pudo publicar el artículo")

    return {"title": title, "url": result["link"], "post_id": result["id"]}
