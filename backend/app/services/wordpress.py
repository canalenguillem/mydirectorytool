import os
import mimetypes
from PIL import Image
import markdown2
import requests
import sqlite3
from bs4 import BeautifulSoup
from decouple import config
from app.models.database import DB_PATH

# Configuració
WP_URL = config("WP_URL")
AUTH = (config("WP_USER"), config("WP_APP_PASS"))
REQUEST_TIMEOUT = 60
MAX_UPLOAD_BYTES = 900_000


def _prepare_media_path(image_path: str) -> str:
    if os.path.getsize(image_path) <= MAX_UPLOAD_BYTES:
        return image_path

    output_dir = os.path.join(os.path.dirname(image_path), ".wordpress")
    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(image_path))[0]
    output_path = os.path.join(output_dir, f"{stem}.jpg")

    with Image.open(image_path) as source:
        image = source.convert("RGB")
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        quality = 85
        while True:
            image.save(output_path, "JPEG", quality=quality, optimize=True)
            if os.path.getsize(output_path) <= MAX_UPLOAD_BYTES or quality <= 55:
                break
            quality -= 10

    print(
        f"[OK] Imatge optimitzada per WordPress: "
        f"{os.path.getsize(image_path)} -> {os.path.getsize(output_path)} bytes"
    )
    return output_path


def _upload_media(image_path: str) -> int | None:
    image_path = _prepare_media_path(image_path)
    filename = os.path.basename(image_path)
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(image_path, "rb") as image:
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
            auth=AUTH,
            files={"file": (filename, image, mime_type)},
            timeout=REQUEST_TIMEOUT,
        )
    if response.status_code != 201:
        print(f"[ERROR] Error pujant {filename}: {response.status_code} -> {response.text}")
        return None
    return response.json().get("id")


def ensure_featured_image(post_id: int, image_path: str) -> bool:
    if not image_path or not os.path.exists(image_path):
        print(f"[ERROR] Imatge destacada local no trobada: {image_path}")
        return False

    image_path = _prepare_media_path(image_path)
    filename = os.path.basename(image_path)
    stem = os.path.splitext(filename)[0]
    media_id = None
    lookup = requests.get(
        f"{WP_URL}/wp-json/wp/v2/media",
        auth=AUTH,
        params={"search": stem, "per_page": 100, "_fields": "id,source_url"},
        timeout=REQUEST_TIMEOUT,
    )
    if lookup.status_code == 200:
        for media in lookup.json():
            if os.path.basename(media.get("source_url", "")) == filename:
                media_id = media.get("id")
                break

    if not media_id:
        media_id = _upload_media(image_path)
    if not media_id:
        return False

    assigned = requests.post(
        f"{WP_URL}/wp-json/wp/v2/restaurante/{post_id}",
        auth=AUTH,
        json={"featured_media": media_id},
        timeout=REQUEST_TIMEOUT,
    )
    if assigned.status_code != 200 or assigned.json().get("featured_media") != media_id:
        print(f"[ERROR] WordPress no ha assignat la destacada al post {post_id}: {assigned.text}")
        return False
    print(f"[OK] Imatge destacada {media_id} assignada al post {post_id}")
    return True


def sync_place_images(post_id: int, place_id: str) -> dict:
    """Synchronize existing local images with an already published post."""
    from app.models.database import get_all_images_for_place

    image_paths = [
        image_path
        for image_path in get_all_images_for_place(place_id)
        if image_path and os.path.exists(image_path)
    ]
    if not image_paths:
        raise RuntimeError("No hay imágenes locales disponibles")

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT image_path FROM place_featured_image WHERE place_id = ?",
            (place_id,),
        ).fetchone()
    finally:
        conn.close()

    featured_path = row[0] if row and row[0] and os.path.exists(row[0]) else image_paths[0]
    if not ensure_featured_image(post_id, featured_path):
        raise RuntimeError("WordPress no pudo asignar la imagen destacada")

    existing_response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/media",
        auth=AUTH,
        params={
            "parent": post_id,
            "per_page": 100,
            "_fields": "id,source_url",
        },
        timeout=REQUEST_TIMEOUT,
    )
    existing_response.raise_for_status()
    existing_by_name = {
        os.path.basename(item.get("source_url", "")): item
        for item in existing_response.json()
        if item.get("source_url")
    }

    gallery_urls = []
    uploaded = 0
    reused = 0
    for image_path in image_paths:
        if image_path == featured_path:
            continue
        prepared_path = _prepare_media_path(image_path)
        filename = os.path.basename(prepared_path)
        media = existing_by_name.get(filename)

        if media:
            media_id = media["id"]
            media_url = media["source_url"]
            reused += 1
        else:
            media_id = _upload_media(prepared_path)
            if not media_id:
                raise RuntimeError(f"No se pudo subir {filename}")
            media_response = requests.get(
                f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                auth=AUTH,
                params={"_fields": "id,source_url"},
                timeout=REQUEST_TIMEOUT,
            )
            media_response.raise_for_status()
            media_url = media_response.json().get("source_url", "")
            uploaded += 1

        assigned = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            auth=AUTH,
            json={"post": post_id},
            timeout=REQUEST_TIMEOUT,
        )
        assigned.raise_for_status()
        if media_url:
            gallery_urls.append(media_url)

    gallery_response = requests.post(
        f"{WP_URL}/wp-json/acf/v3/restaurante/{post_id}",
        auth=AUTH,
        json={"fields": {"place_gallery": ",".join(gallery_urls)}},
        timeout=REQUEST_TIMEOUT,
    )
    gallery_response.raise_for_status()

    return {
        "available": len(image_paths),
        "gallery": len(gallery_urls),
        "uploaded": uploaded,
        "reused": reused,
    }

def get_or_create_category(cpostal: str) -> int | None:
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?search={cpostal}", auth=AUTH)
    
    if r.status_code != 200:
        print(f"[ERROR] No s'ha pogut obtenir categories. Status: {r.status_code}")
        print(f"Resposta: {r.text}")
        return None

    try:
        results = r.json()
    except Exception as e:
        print(f"[ERROR] JSON Decode Error: {e}")
        print(f"Resposta del servidor: {r.text}")
        return None

    if results:
        return results[0]["id"]

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/categories", auth=AUTH, json={"name": cpostal})
    if r.status_code == 201:
        return r.json()["id"]
    else:
        print(f"[ERROR] No s'ha pogut crear la categoria. Status: {r.status_code}")
        print(f"Resposta: {r.text}")
    return None

def publicar_article_restaurante(data: dict) -> int | None:
    from app.models.database import get_all_images_for_place

    article_path = data.get("article_path")
    if not article_path or not os.path.exists(article_path):
        print(f"[ERROR] No s'ha trobat el fitxer .md: {article_path}")
        return None

    try:
        with open(article_path, "r") as f:
            md_text = f.read()
        # Eliminar el título H1 y el bloque SEO final (META-DESCRIPCIÓN, PALABRAS CLAVE, etc.)
        lines = md_text.splitlines()
        content_lines = [l for i, l in enumerate(lines) if not (i == 0 and l.startswith("# "))]
        # Eliminar todo a partir del último --- que precede al bloque SEO
        seo_keywords = ("**META-DESCRIPCIÓN", "**LLAMADA A LA ACCIÓN", "**PALABRAS CLAVE")
        cutoff = None
        for i, l in enumerate(content_lines):
            if any(l.strip().startswith(k) for k in seo_keywords):
                # Retroceder para incluir el --- separador
                cutoff = i - 1 if i > 0 and content_lines[i-1].strip() == "---" else i
                break
        if cutoff is not None:
            content_lines = content_lines[:cutoff]

        # Strip "Llamada a la acción final" section but keep phone/website block after ---
        cta_start = None
        for i, l in enumerate(content_lines):
            if l.strip().startswith("## Llamada a la acción"):
                cta_start = i
                break
        if cta_start is not None:
            phone_lines = []
            sep_count = 0
            in_phone_block = False
            for i in range(cta_start, len(content_lines)):
                if content_lines[i].strip() == "---":
                    sep_count += 1
                    if sep_count == 1:
                        in_phone_block = True
                    else:
                        break
                elif in_phone_block:
                    phone_lines.append(content_lines[i])
            content_lines = content_lines[:cta_start] + phone_lines

        html_content = markdown2.markdown("\n".join(content_lines), extras=["linkify"])
        soup = BeautifulSoup(html_content, "html.parser")
        for a in soup.find_all("a", href=True):
            a["target"] = "_blank"
            a["rel"] = "noopener noreferrer"
        html_content = str(soup)
    except Exception as e:
        print(f"[ERROR] Error llegint/converntint markdown: {e}")
        return None

    featured_image_path = None
    place_id = data.get("place_id")
    if place_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT image_path FROM place_featured_image WHERE place_id = ?", (place_id,))
        row = c.fetchone()
        conn.close()
        if row:
            featured_image_path = row[0]

    # La destacada se sube antes de crear el post y se incluye en la misma
    # petición. Si falla, no se crea una ficha incompleta.
    if not featured_image_path or not os.path.exists(featured_image_path):
        print(f"[ERROR] No hi ha imatge destacada local per {place_id}")
        return None
    featured_media_id = _upload_media(featured_image_path)
    if not featured_media_id:
        return None

    post_data = {
        "title": data["title"],
        "content": html_content,
        "excerpt": data.get("excerpt", ""),
        "status": "publish",
        "categories": [data["categoria_id"]] if data.get("categoria_id") else [],
        "featured_media": featured_media_id,
    }

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/restaurante", auth=AUTH, json=post_data)
    if r.status_code != 201:
        print(f"[ERROR] Error al publicar: {r.status_code} -> {r.text}")
        return None

    response = r.json()
    post_id = response.get("id")
    post_link = response.get("link", "")
    data["wp_url"] = post_link
    print(f"[OK] Publicat: {post_link}")

    # Verificación explícita: publicar no se considera correcto si WordPress
    # ignora la imagen indicada al crear el post.
    if response.get("featured_media") != featured_media_id:
        if not ensure_featured_image(post_id, featured_image_path):
            print(f"[ERROR] El post {post_id} ha quedat sense destacada")

    # 🖼️ Pujar imatges addicionals i recollir URLs
    image_paths = get_all_images_for_place(place_id)
    gallery_urls = []
    for img_path in image_paths:
        if not os.path.exists(img_path) or img_path == featured_image_path:
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
                img_url = media_res.json().get("source_url")
                gallery_urls.append(img_url)
                # Associar al post
                media_id = media_res.json().get("id")
                requests.post(
                    f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                    auth=AUTH,
                    json={"post": post_id}
                )
                print(f"[OK] Imatge {filename} pujada i associada al post")
            else:
                print(f"[ERROR] Error pujant imatge {filename}: {media_res.status_code} -> {media_res.text}")

    # 🔗 Guardar les URLs de la galeria al custom field ACF (place_gallery)
    if gallery_urls:
        urls_str = ",".join(gallery_urls)
        acf_payload = {"fields": {"place_gallery": urls_str}}
        acf_res = requests.post(
            f"{WP_URL}/wp-json/acf/v3/restaurante/{post_id}",
            auth=AUTH,
            json=acf_payload
        )
        if acf_res.status_code == 200:
            print(f"[OK] Camp place_gallery actualitzat amb {len(gallery_urls)} imatges")
        else:
            print(f"[ERROR] Error guardant place_gallery: {acf_res.status_code} -> {acf_res.text}")

    return post_id

def guardar_campos_acf(post_id: int, acf_data: dict):
    r = requests.post(
        f"{WP_URL}/wp-json/acf/v3/restaurante/{post_id}",
        auth=AUTH,
        json={"fields": acf_data}
    )
    if r.status_code == 200:
        print(f"[OK] Camps ACF guardats")
        return True
    else:
        print(f"[ERROR] ACF: {r.status_code} -> {r.text}")
        return False
