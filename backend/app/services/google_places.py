import requests
from decouple import config


REQUEST_TIMEOUT = 20

def buscar_lugares(query):
    endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": config("GOOGLE_API_KEY")}
    response = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json().get("results", [])

def get_reviews(place_id):
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "reviews",
        "key": config("GOOGLE_API_KEY")
    }
    response = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    return data.get("result", {}).get("reviews", [])

def get_place_details(place_id):
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,international_phone_number,adr_address,reviews",
        "key": config("GOOGLE_API_KEY")
    }
    response = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
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


def _component(components: list[dict], *types: str, short: bool = False) -> str:
    for component_type in types:
        for component in components:
            if component_type in component.get("types", []):
                key = "short_name" if short else "long_name"
                return component.get(key, "")
    return ""


def get_contact_and_location(place_id: str) -> dict:
    """Obtain contact and structured location in a single Details request."""
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": (
            "address_components,geometry,international_phone_number,"
            "website,business_status"
        ),
        "key": config("GOOGLE_API_KEY"),
    }
    response = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    status = payload.get("status")
    if status != "OK":
        raise RuntimeError(f"Google Place Details devolvió {status or 'sin estado'}")

    data = payload.get("result", {})
    components = data.get("address_components", [])
    location = data.get("geometry", {}).get("location", {})
    return {
        "postal_code": _component(components, "postal_code"),
        "country": _component(components, "country"),
        "country_code": _component(components, "country", short=True),
        "region": _component(components, "administrative_area_level_1"),
        "province": _component(components, "administrative_area_level_2"),
        "municipality": _component(components, "administrative_area_level_3", "locality"),
        "city": _component(components, "locality", "postal_town", "administrative_area_level_3"),
        "district": _component(components, "sublocality_level_1", "neighborhood"),
        "latitude": location.get("lat"),
        "longitude": location.get("lng"),
        "phone": data.get("international_phone_number", ""),
        "website": data.get("website", ""),
        "business_status": data.get("business_status", ""),
        # Google Places no ofrece email. Se conserva vacío para incorporarlo
        # más adelante desde una fuente verificada y con su procedencia.
        "email": "",
        "email_source": "",
    }


