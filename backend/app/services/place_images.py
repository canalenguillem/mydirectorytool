import os
import requests
from decouple import config

import os as _os
IMAGES_DIR = _os.path.join(_os.environ.get("DATA_DIR", "."), "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

def clean_folder_name(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name)

def get_place_name(place_id: str) -> str:
    url = (
        f"https://maps.googleapis.com/maps/api/place/details/json?"
        f"place_id={place_id}&fields=name&key={config('GOOGLE_API_KEY')}"
    )
    r = requests.get(url)
    result = r.json().get("result", {})
    return result.get("name", f"place_{place_id}")

def get_photo_references(place_id: str) -> list[str]:
    url = (
        f"https://maps.googleapis.com/maps/api/place/details/json?"
        f"place_id={place_id}&fields=photos&key={config('GOOGLE_API_KEY')}"
    )
    r = requests.get(url)
    result = r.json().get("result", {})
    photos = result.get("photos", [])
    return [p["photo_reference"] for p in photos]

def download_all_place_photos(place_id: str) -> list[str]:
    place_name = get_place_name(place_id)
    folder_name = clean_folder_name(place_name)
    place_dir = os.path.join(IMAGES_DIR, folder_name)
    os.makedirs(place_dir, exist_ok=True)

    photo_refs = get_photo_references(place_id)
    saved_paths = []

    for i, ref in enumerate(photo_refs):
        photo_url = (
            f"https://maps.googleapis.com/maps/api/place/photo?"
            f"maxwidth=1600&photo_reference={ref}&key={config('GOOGLE_API_KEY')}"
        )
        print(f"[INFO] Descargando imagen {idx}/{len(photo_refs)} para {place_id}")
        r = requests.get(photo_url, stream=True)
        if r.status_code == 200:
            content_type = r.headers.get("Content-Type", "")
            ext = content_type.split("/")[-1] if "/" in content_type else "jpg"
            filename = f"{place_id}_{i+1}.{ext}"
            filepath = os.path.join(place_dir, filename)

            with open(filepath, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

            saved_paths.append(filepath)

    return saved_paths
def get_all_images_for_place(place_id: str) -> list[str]:
    place_name = get_place_name(place_id)
    folder_name = clean_folder_name(place_name)
    place_dir = os.path.join(IMAGES_DIR, folder_name)

    if not os.path.exists(place_dir):
        return []

    image_files = []
    for file in os.listdir(place_dir):
        if file.startswith(place_id) and not file.endswith(("-150x150.jpg", "-225x300.jpg")):
            image_files.append(os.path.join(place_dir, file))

    return image_files
