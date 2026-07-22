import os
import markdown2
import requests
import sqlite3
from bs4 import BeautifulSoup
from decouple import config
from app.models.database import DB_PATH

# Configuració
WP_URL = config("WP_URL")
AUTH = (config("WP_USER"), config("WP_APP_PASS"))

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

    post_data = {
        "title": data["title"],
        "content": html_content,
        "excerpt": data.get("excerpt", ""),
        "status": "publish",
        "categories": [data["categoria_id"]] if data.get("categoria_id") else []
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

    # 🖼️ Pujar imatge destacada
    if featured_image_path and os.path.exists(featured_image_path):
        with open(featured_image_path, "rb") as img:
            filename = os.path.basename(featured_image_path)
            media_res = requests.post(
                f"{WP_URL}/wp-json/wp/v2/media",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
                auth=AUTH,
                files={"file": img}
            )
            if media_res.status_code == 201:
                media_id = media_res.json().get("id")
                requests.post(
                    f"{WP_URL}/wp-json/wp/v2/restaurante/{post_id}",
                    auth=AUTH,
                    json={"featured_media": media_id}
                )
                print(f"[OK] Imatge destacada assignada")
            else:
                print(f"[ERROR] Error pujant imatge destacada: {media_res.status_code} -> {media_res.text}")

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
