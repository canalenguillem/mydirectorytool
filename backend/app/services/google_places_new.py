import logging
import os
import time

import requests
from decouple import config

from app.services.google_places_usage import record_google_places_usage

logger = logging.getLogger(__name__)

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
REQUEST_TIMEOUT = 20

# Campos baratos para el paso de descubrimiento -- nada de fotos, reseñas
# ni horario aquí. Los campos "caros" siguen pidiéndose después, solo para
# los candidatos ya seleccionados como top-N (ver place_ranking.py), vía
# el Details Legacy ya existente (get_contact_and_location).
DISCOVERY_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.rating,places.userRatingCount,places.location,"
    "places.businessStatus,nextPageToken"
)


def search_text_new(query: str, page_token: str | None = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": config("GOOGLE_API_KEY"),
        "X-Goog-FieldMask": DISCOVERY_FIELD_MASK,
    }
    body = {"textQuery": query, "languageCode": "es"}
    if page_token:
        body["pageToken"] = page_token
    response = requests.post(
        TEXT_SEARCH_URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def discover_candidates(
    query: str,
    max_pages: int = 3,
    seed_location_id: int | None = None,
    country_code: str | None = None,
    directory_search_term: str | None = None,
) -> list[dict]:
    """Hasta max_pages * 20 candidatos (máx. 60 con max_pages=3), deduplicados
    por id. Cada página consumida se registra en google_places_usage,
    incluida cualquier página que falle."""
    page_delay = float(os.environ.get("GOOGLE_TEXT_SEARCH_PAGE_DELAY_SECONDS", "2"))
    results: list[dict] = []
    seen_ids: set[str] = set()
    page_token = None

    for _ in range(max_pages):
        try:
            payload = search_text_new(query, page_token)
        except requests.HTTPError as exc:
            status = (
                str(exc.response.status_code) if exc.response is not None else "ERROR"
            )
            record_google_places_usage(
                "text_search_new",
                "v1",
                DISCOVERY_FIELD_MASK,
                query,
                seed_location_id,
                country_code,
                directory_search_term,
                result_count=0,
                status=status,
            )
            raise

        places = payload.get("places", [])
        record_google_places_usage(
            "text_search_new",
            "v1",
            DISCOVERY_FIELD_MASK,
            query,
            seed_location_id,
            country_code,
            directory_search_term,
            result_count=len(places),
            status="OK",
        )
        for place in places:
            place_id = place.get("id")
            if place_id and place_id not in seen_ids:
                seen_ids.add(place_id)
                results.append(place)

        page_token = payload.get("nextPageToken")
        if not page_token:
            break
        time.sleep(page_delay)

    return results


def normalize_candidate(place: dict) -> dict:
    """Adapta la forma de Places API (New) a la forma "estilo Legacy" que ya
    consume el bucle de inserción de database.py (name, formatted_address,
    place_id, rating, geometry.location), para reutilizarlo tal cual."""
    location = place.get("location", {})
    return {
        "place_id": place.get("id", ""),
        "name": place.get("displayName", {}).get("text", ""),
        "formatted_address": place.get("formattedAddress", ""),
        "rating": place.get("rating"),
        "user_ratings_total": place.get("userRatingCount") or 0,
        "business_status": place.get("businessStatus", ""),
        "geometry": {
            "location": {
                "lat": location.get("latitude"),
                "lng": location.get("longitude"),
            }
        },
    }
