from fastapi import APIRouter, Query
from app.services.google_places import buscar_lugares
from app.models.database import init_db, get_or_create_search
from app.services.featured_image import set_featured_image
import sqlite3
from app.models.database import DB_PATH
import random



router = APIRouter()

@router.on_event("startup")
def startup_event():
    init_db()

from unidecode import unidecode

@router.get("/search")
def search_places(query: str = Query(..., min_length=1)):
    query = query.strip()
    query = unidecode(query)  # elimina accents
    lugares = get_or_create_search(query)
    return {"resultados": lugares}


@router.get("/saved")
def list_saved_places():
    from app.models.database import list_all_places
    return {"guardats": list_all_places()}


@router.post("/save")
def save_place(place_id: str):
    from fastapi import HTTPException
    from app.models.database import save_search_result

    place = save_search_result(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Resultado de búsqueda no encontrado")
    return {"message": "Restaurante guardado", "place": place}


@router.get("/reviews")
def fetch_and_save_reviews(place_id: str):
    from app.services.google_places import get_reviews
    from app.models.database import save_reviews_for_place

    reviews = get_reviews(place_id)
    if not reviews:
        return {"message": "No s'han trobat ressenyes."}
    save_reviews_for_place(place_id, reviews)
    return {"message": f"S'han guardat {len(reviews)} ressenyes.", "reviews": reviews}


@router.get("/reviews/concat")
def get_reviews_text(place_id: str):
    from app.models.database import get_or_create_concatenated_reviews
    text = get_or_create_concatenated_reviews(place_id)
    return {"place_id": place_id, "text": text}

@router.get("/reviews/info")
def get_full_review_info(place_id: str):
    from app.models.database import get_or_create_review_info
    return get_or_create_review_info(place_id)

from pydantic import BaseModel

class BlogRequest(BaseModel):
    place_id: str
    lang: str = "es"

@router.post("/blog")
def generar_blog(data: BlogRequest):
    place_id = data.place_id
    lang = data.lang

    from app.models.database import get_or_create_review_info, get_or_create_article
    from app.services.openai_writer import generar_articulo_blog

    info = get_or_create_review_info(place_id)
    article = get_or_create_article(info, lang, generar_articulo_blog)

    return {"title": f"Artículo para {info['name']} en {lang}", "content": article}
@router.get("/blog/articles")
def llistar_articles_generats():
    from app.models.database import get_all_articles
    return {"articles": get_all_articles()}

@router.delete("/blog/article")
def eliminar_article(place_id: str, lang: str = "es"):
    from app.models.database import delete_article
    success, message = delete_article(place_id, lang)
    return {"success": success, "message": message}

@router.get("/export/jsons")
def exportar_reviews_json():
    from app.models.database import exportar_reviews_a_json
    total, arxius = exportar_reviews_a_json()
    return {"success": True, "total_exportats": total, "fitxers": arxius}

@router.get("/places/by-postal")
def buscar_places_per_codi_postal(postal_code: str):
    from app.models.database import get_places_by_postal_code
    results = get_places_by_postal_code(postal_code)
    if results:
        return {"postal_code": postal_code, "results": results}
    else:
        return {"postal_code": postal_code, "results": [], "message": "No se han encontrado lugares con ese código postal."}


@router.post("/places/download-images")
def descargar_imagenes(place_id: str):
    from app.services.place_images import download_all_place_photos
    import sqlite3
    from app.models.database import DB_PATH

    rutas = download_all_place_photos(place_id)
    if not rutas:
        return {"error": "No se encontraron imágenes para este lugar"}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    nuevas = 0
    for ruta in rutas:
        # Comprovem si ja existeix aquesta imatge
        c.execute("SELECT 1 FROM place_image WHERE place_id = ? AND image_path = ?", (place_id, ruta))
        if c.fetchone():
            continue
        c.execute("""
            INSERT INTO place_image (place_id, image_path)
            VALUES (?, ?)
        """, (place_id, ruta))
        nuevas += 1

    conn.commit()
    conn.close()

    return {
        "message": f"{nuevas} imatges noves registrades",
        "imagenes": rutas
    }


@router.post("/places/featured-image")
def definir_imatge_destacada(place_id: str, image_path: str):
    import sqlite3
    from app.models.database import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Esborrar qualsevol entrada anterior
    c.execute("DELETE FROM place_featured_image WHERE place_id = ?", (place_id,))

    # Inserir la nova imatge destacada
    c.execute("""
        INSERT INTO place_featured_image (place_id, image_path)
        VALUES (?, ?)
    """, (place_id, image_path))

    conn.commit()
    conn.close()

    return {
        "message": f"Imatge destacada definida per {place_id}",
        "imatge": image_path
    }


@router.post("/places/set-featured-random")
def set_featured_random(place_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Obtenir totes les imatges del place_id
    c.execute("SELECT image_path FROM place_image WHERE place_id = ?", (place_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return {"error": "No s'han trobat imatges per aquest place_id"}

    # Convertim a llista simple
    image_paths = [r[0] for r in rows]

    # Triem-ne una a l’atzar
    selected_image = random.choice(image_paths)

    # Guardar amb la funció del servei
    set_featured_image(place_id, selected_image)

    return {"message": f"Imatge destacada assignada: {selected_image}"}


@router.delete("/places/delete")
def delete_place_complet(place_id: str):
    from app.services.place_deletion import delete_place_completely

    return delete_place_completely(place_id)



