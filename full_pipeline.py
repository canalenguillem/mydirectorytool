import sys
import requests

API_BASE = "http://localhost:8000"

def call_endpoint_get(path,place_id):
    url = f"{API_BASE}{path}"
    print(f"▶ Calling {url}")
    response = requests.get(url, params={"place_id": place_id})
    if response.status_code == 200:
        print(f"✅ OK: {response.json()}")
    else:
        print(f"❌ ERROR {response.status_code}: {response.text}")
    return response

def call_endpoint(path, place_id):
    url = f"{API_BASE}{path}"
    print(f"▶ Calling {url}")
    response = requests.post(url, params={"place_id": place_id})
    if response.status_code == 200:
        print(f"✅ OK: {response.json()}")
    else:
        print(f"❌ ERROR {response.status_code}: {response.text}")
    return response

def call_generate_blog(place_id, lang="es"):
    payload = {
        "place_id": place_id,
        "lang": lang
    }
    response = requests.post(f"{API_BASE}/places/blog", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Generat article: {data['title']}")
    else:
        print(f"[ERROR] Status {response.status_code}: {response.text}")

def full_pipeline(place_id):
    #ger reviews
    call_endpoint_get("/places/reviews",place_id)
    call_endpoint_get("/places/reviews/concat",place_id)


    # # 1️⃣ Generar article
    call_generate_blog(place_id)

    # # 2️⃣ Descarregar imatges
    call_endpoint("/places/places/download-images", place_id)

    # # 3️⃣ Posar featured aleatòria
    call_endpoint("/places/places/set-featured-random", place_id)

    # # 4️⃣ Publicar article final
    call_endpoint("/blog/blog/publish", place_id)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usa: python full_pipeline.py <place_id>")
        sys.exit(1)
    
    place_id = sys.argv[1]
    full_pipeline(place_id)
