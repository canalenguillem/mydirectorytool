import requests
import argparse
from decouple import config

API_KEY = config("GOOGLE_API_KEY")

def get_place_id(nombre_lugar, localidad="Sineu, Mallorca"):
    endpoint = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": f"{nombre_lugar} {localidad}",
        "inputtype": "textquery",
        "fields": "place_id",
        "key": API_KEY
    }
    response = requests.get(endpoint, params=params)
    data = response.json()
    if data["candidates"]:
        return data["candidates"][0]["place_id"]
    return None

def get_reviews(place_id):
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,rating,reviews",
        "key": API_KEY
    }
    response = requests.get(endpoint, params=params)
    data = response.json()
    return data.get("result", {}).get("reviews", [])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obtener reseñas de un lugar con Google Places API")
    parser.add_argument("--query", required=True, help="Nombre del restaurante o lugar")
    args = parser.parse_args()

    place_id = get_place_id(args.query)
    if place_id:
        print(f"Place ID encontrado: {place_id}")
        reviews = get_reviews(place_id)
        for r in reviews:
            print(f"Autor: {r['author_name']}")
            print(f"Puntuación: {r['rating']}")
            print(f"Comentario: {r['text']}\n{'-'*40}\n")
    else:
        print("No se encontró el lugar.")
