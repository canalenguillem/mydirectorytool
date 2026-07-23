from fastapi import APIRouter
from app.models.database import (
    enrich_place_details,
    get_article_data,
    marcar_publicado,
    set_place_food_type,
)
from app.services.wordpress import publicar_article_restaurante, guardar_campos_acf, get_or_create_category
from app.services.comida_classifier import detectar_tipo_comida
from app.services.openai_writer import generar_excerpt
from decouple import config
from bs4 import BeautifulSoup
import requests
import os



router = APIRouter()

WP_URL = config("WP_URL")
AUTH = (config("WP_USER"), config("WP_APP_PASS"))


def acf_fields_from_data(data: dict) -> dict:
    return {
        "telefono": data.get("phone", ""),
        "web": data.get("website", ""),
        "codigo_postal": data.get("postal_code", ""),
        "email": data.get("email", ""),
        "ciudad": data.get("city", ""),
        "municipio": data.get("municipality", ""),
        "provincia": data.get("province", ""),
        "region": data.get("region", ""),
        "pais": data.get("country", ""),
        "codigo_pais": data.get("country_code", ""),
        "distrito": data.get("district", ""),
        "latitud": data.get("latitude"),
        "longitud": data.get("longitude"),
        "tipo_de_comida": data.get("tipo_de_comida", ""),
        "place_id": data.get("place_id", ""),
    }

@router.post("/blog/publish")
def publicar_article(place_id: str):
    try:
        enrich_place_details(place_id)
    except Exception as exc:
        return {"error": f"No se pudieron completar los datos del restaurante: {exc}"}

    data = get_article_data(place_id)
    if not data:
        return {"error": "No se encontró el artículo"}

    if data.get("publicado_en_wp"):
        return {"message": "Ya publicado anteriormente"}

    categoria_id = get_or_create_category(data.get("postal_code"))
    data["categoria_id"] = categoria_id
    data["tipo_de_comida"] = detectar_tipo_comida(data["content"])
    set_place_food_type(place_id, data["tipo_de_comida"])
    print(f'tipo de comida {data["tipo_de_comida"]} ')
    data["excerpt"] = generar_excerpt(data["content"])


    post_id = publicar_article_restaurante(data)
    data["place_id"]=place_id
    if not post_id:
        return {"error": "Error al crear el post"}

    guardar_campos_acf(post_id, acf_fields_from_data(data))

    marcar_publicado(place_id, post_id)
    return {"message": "Artículo publicado", "post_id": post_id}


@router.post("/blog/actualizar-excerpts")
def actualizar_excerpts_faltantes():
    url = f"{WP_URL}/wp-json/wp/v2/restaurante?per_page=100"
    r = requests.get(url, auth=AUTH)
    posts = r.json()

    total = len(posts)
    actualizados = 0
    detalles = []

    for post in posts:
        post_id = post["id"]
        title = post["title"]["rendered"]
        rendered_excerpt = post.get("excerpt", {}).get("rendered", "")

        # Si el excerpt NO conté "Leer más", assumim que ja hi ha un de personalitzat
        if "Leer más" not in rendered_excerpt:
            continue

        # Obtenim el contingut complet i generam un excerpt amb OpenAI
        content = post.get("content", {}).get("rendered", "")
        plain_text = BeautifulSoup(content, "html.parser").get_text()
        nuevo_excerpt = generar_excerpt(plain_text)

        # Enviam la petició per actualitzar-lo
        patch_data = {
            "excerpt": nuevo_excerpt
        }
        patch_url = f"{WP_URL}/wp-json/wp/v2/restaurante/{post_id}"
        patch_r = requests.post(patch_url, auth=AUTH, json=patch_data)

        if patch_r.status_code == 200:
            actualizados += 1
            detalles.append(f"Post {post_id} actualizado: {title}")
        else:
            detalles.append(f"Error al actualizar post {post_id}: {patch_r.text}")

    return {
        "total": total,
        "actualizados": actualizados,
        "detalles": detalles
    }


@router.delete("/blog/delete")
def borrar_article_y_fotos_wordpress(place_id: str):
    # 1️⃣ Buscar post amb aquest place_id
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/restaurante?per_page=100", auth=AUTH)
    if r.status_code != 200:
        return {"error": f"Error obteniendo posts: {r.text}"}

    posts = r.json()
    post_to_delete = None

    for post in posts:
        acf_fields = post.get("acf", {})
        if acf_fields.get("place_id") == place_id:
            post_to_delete = post
            break

    if not post_to_delete:
        return {"error": "Post no encontrado en WordPress"}

    post_id = post_to_delete["id"]

    # 2️⃣ Buscar media (imatges) associades al post
    media_r = requests.get(f"{WP_URL}/wp-json/wp/v2/media?parent={post_id}", auth=AUTH)
    media_items = media_r.json() if media_r.status_code == 200 else []

    deleted_images = []

    # 3️⃣ Esborrar imatges
    for media in media_items:
        media_id = media["id"]
        media_del_r = requests.delete(f"{WP_URL}/wp-json/wp/v2/media/{media_id}?force=true", auth=AUTH)
        if media_del_r.status_code == 200:
            deleted_images.append(media_id)

    # 4️⃣ Esborrar el post
    del_r = requests.delete(f"{WP_URL}/wp-json/wp/v2/restaurante/{post_id}?force=true", auth=AUTH)
    if del_r.status_code != 200:
        return {"error": f"Error al eliminar post: {del_r.text}"}

    return {
        "message": f"Post {post_id} eliminado correctamente",
        "deleted_images": deleted_images
    }


from app.services.wordpress import publicar_article_restaurante, guardar_campos_acf, get_or_create_category
from app.services.comida_classifier import detectar_tipo_comida
from app.services.openai_writer import generar_excerpt
from app.services.place_images import download_all_place_photos
from app.services.featured_image import set_featured_image  # Assumeix que tens aquest servei
from app.services.place_images import get_all_images_for_place


def pujar_i_associar_imatges_addicionals(place_id, post_id):
    from app.models.database import get_all_images_for_place
    image_paths = get_all_images_for_place(place_id)
    uploaded_urls = []

    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"[WARN] Imatge no trobada: {img_path}")
            continue

        with open(img_path, "rb") as img:
            filename = os.path.basename(img_path)
            media_res = requests.post(
                f"{WP_URL}/wp-json/wp/v2/media",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
                auth=AUTH,
                files={"file": img}
            )

        if media_res.status_code == 201:
            media_data = media_res.json()
            media_id = media_data.get("id")
            media_url = media_data.get("source_url")

            # Associar la imatge al post
            patch_res = requests.post(
                f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                auth=AUTH,
                json={"post": post_id}
            )

            if patch_res.status_code == 200:
                uploaded_urls.append(media_url)
                print(f"[OK] Imatge {filename} pujada i associada")
            else:
                print(f"[ERROR] No s'ha pogut associar {filename}: {patch_res.status_code} -> {patch_res.text}")
        else:
            print(f"[ERROR] Error pujant {filename}: {media_res.status_code} -> {media_res.text}")

    # Guardar les URLs al camp ACF (si tens activat place_gallery)
    if uploaded_urls:
        acf_res = requests.post(
            f"{WP_URL}/wp-json/acf/v3/restaurante/{post_id}",
            auth=AUTH,
            json={"fields": {"place_gallery": ",".join(uploaded_urls)}}
        )
        if acf_res.status_code == 200:
            print(f"[OK] Galeria ACF actualitzada")
        else:
            print(f"[ERROR] No s'ha pogut actualitzar ACF: {acf_res.status_code} -> {acf_res.text}")


@router.post("/blog/full-publish")
def full_publish(place_id: str):
    try:
        enrich_place_details(place_id)
    except Exception as exc:
        return {"error": f"No se pudieron completar los datos del restaurante: {exc}"}

    data = get_article_data(place_id)
    if not data:
        return {"error": f"No s'ha trobat article per {place_id}"}

    # Evita crear un segon post y volver a subir sus imágenes si se repite
    # accidentalmente la petición.
    if data.get("publicado_en_wp") and data.get("wp_url"):
        return {
            "message": "El artículo ya estaba publicado",
            "post_id": data.get("wp_post_id"),
        }

    # Toda la preparación debe hacerse antes de delegar la publicación. La
    # función publicar_article_restaurante es la única responsable de subir la
    # imagen destacada y la galería.
    data["categoria_id"] = get_or_create_category(data.get("postal_code"))
    data["tipo_de_comida"] = detectar_tipo_comida(data["content"])
    set_place_food_type(place_id, data["tipo_de_comida"])
    data["excerpt"] = generar_excerpt(data["content"])

    post_id = publicar_article_restaurante(data)
    if not post_id:
        return {"error": "Error al publicar article"}

    guardar_campos_acf(post_id, acf_fields_from_data(data))

    marcar_publicado(place_id, post_id, data.get("wp_url"))
    return {"message": "Artículo publicado correctamente", "post_id": post_id}
