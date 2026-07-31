import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.database import (
    create_roundup_job,
    get_all_images_for_place,
    get_basket,
    get_places_by_ids,
    has_active_roundup_job_for_basket,
    list_roundup_jobs,
)
from app.services.publication_queue import enqueue_specific_places, resume_queue as resume_publication_queue
from app.services.roundup_queue import activate_queue, get_queue_status
from app.services.roundup_queue import start_worker as start_roundup_worker
from app.services.roundup_writer import generar_articulo_resumen, generar_excerpt_resumen, insertar_imagenes
from app.services.wordpress import (
    actualizar_post_generico,
    crear_post_generico,
    markdown_a_html_restaurante,
    obtener_post_publicado,
    upload_media,
)

router = APIRouter()


class RoundupRequest(BaseModel):
    tema: str
    place_ids: list[str]
    post_id: int | None = None
    basket_id: int | None = None


def build_and_publish_roundup(tema: str, place_ids: list[str], post_id: int | None = None) -> dict:
    """Genera el artículo de resumen y lo publica/actualiza en WordPress.
    Asume que todas las fichas ya están publicadas -- lanza ValueError si
    no, tanto para el endpoint síncrono como para roundup_queue (que ya
    debería haberlo comprobado antes de llamar, pero se revalida aquí por
    si el estado cambió entre medias)."""
    if len(place_ids) < 2:
        raise ValueError("Selecciona al menos 2 fichas")

    places = get_places_by_ids(place_ids)
    if len(places) != len(place_ids):
        raise ValueError("Alguna de las fichas seleccionadas ya no existe")

    lugares = []
    for place in places:
        if not place["publicado_en_wp"] or not place["wp_post_id"]:
            raise ValueError(f"{place['name']} todavía no está publicada")
        published = obtener_post_publicado(int(place["wp_post_id"]))
        if not published:
            raise ValueError(f"No se pudo leer la ficha publicada de {place['name']}")
        lugares.append(
            {
                "name": place["name"],
                "city": place["city"] or place["municipality"] or "",
                "rating": place["rating"],
                "url": published["link"],
                "excerpt": published["excerpt"] or published["title"],
                "image_url": published.get("image_url", ""),
            }
        )

    md_text = generar_articulo_resumen(tema, lugares)
    title_match = re.search(r"^# (.+)", md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else tema
    md_text = insertar_imagenes(md_text, lugares)
    html_content = markdown_a_html_restaurante(md_text)
    excerpt = generar_excerpt_resumen(md_text)

    # Imagen destacada: la primera imagen local disponible de la ficha
    # mejor valorada de la selección -- sin pedirle al usuario que elija.
    featured_media_id = None
    best_place = max(places, key=lambda p: p["rating"] or 0)
    images = get_all_images_for_place(best_place["place_id"])
    if images:
        featured_media_id = upload_media(images[0])

    if post_id:
        result = actualizar_post_generico(post_id, title, html_content, excerpt, featured_media_id)
    else:
        result = crear_post_generico(title, html_content, excerpt, featured_media_id)
    if not result:
        raise RuntimeError("No se pudo publicar el artículo")

    return {"title": title, "url": result["link"], "post_id": result["id"]}


@router.post("/generate")
def generate_roundup(data: RoundupRequest):
    try:
        return build_and_publish_roundup(data.tema, data.place_ids, data.post_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/queue")
def queue_roundup(data: RoundupRequest):
    if len(data.place_ids) < 2:
        raise HTTPException(status_code=400, detail="Selecciona al menos 2 fichas")
    if data.basket_id is not None:
        basket = get_basket(data.basket_id)
        if not basket:
            raise HTTPException(status_code=404, detail="Cesta no encontrada")
        if basket["published_post_id"]:
            raise HTTPException(
                status_code=400,
                detail="Esta cesta ya tiene un artículo publicado -- crea otra cesta para uno nuevo",
            )
        if has_active_roundup_job_for_basket(data.basket_id):
            raise HTTPException(
                status_code=400,
                detail="Esta cesta ya tiene un artículo en curso -- espera a que termine",
            )
    places = get_places_by_ids(data.place_ids)
    if len(places) != len(data.place_ids):
        raise HTTPException(status_code=404, detail="Alguna de las fichas seleccionadas ya no existe")

    job = create_roundup_job(data.tema, data.place_ids, data.post_id, data.basket_id)

    # Encolar de una sola vez, al crear el trabajo -- no en cada tick del
    # worker, para no reintentar sin límite una ficha que ya falló varias
    # veces en publication_queue (ver _stuck_place_names en roundup_queue).
    unpublished_ids = [
        p["place_id"] for p in places if not p["publicado_en_wp"] or not p["wp_post_id"]
    ]
    if unpublished_ids:
        enqueue_specific_places(unpublished_ids)
        resume_publication_queue()

    start_roundup_worker()
    activate_queue()
    return job


@router.get("/queue/status")
def roundup_queue_status():
    return get_queue_status()


@router.get("/queue/jobs")
def roundup_queue_jobs(limit: int = 20):
    return {"jobs": list_roundup_jobs(limit)}
