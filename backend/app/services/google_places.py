import requests
from decouple import config

def buscar_lugares(query):
    endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": config("GOOGLE_API_KEY")}
    response = requests.get(endpoint, params=params)
    return response.json().get("results", [])

def get_reviews(place_id):
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "reviews",
        "key": config("GOOGLE_API_KEY")
    }
    response = requests.get(endpoint, params=params)
    data = response.json()
    return data.get("result", {}).get("reviews", [])

def get_place_details(place_id):
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,international_phone_number,adr_address,reviews",
        "key": config("GOOGLE_API_KEY")
    }
    response = requests.get(endpoint, params=params)
    return response.json().get("result", {})

def get_postal_code(place_id):
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "address_components",
        "key": config("GOOGLE_API_KEY")
    }
    response = requests.get(endpoint, params=params)
    data = response.json()

    components = data.get("result", {}).get("address_components", [])
    for comp in components:
        if "postal_code" in comp.get("types", []):
            return comp.get("long_name")
    return ""

def get_extra_details(place_id):
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "international_phone_number,website",
        "key": config("GOOGLE_API_KEY")
    }
    response = requests.get(endpoint, params=params)
    data = response.json().get("result", {})
    return {
        "phone": data.get("international_phone_number", ""),
        "website": data.get("website", "")
    }



