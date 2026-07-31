from decouple import config
from fastapi import APIRouter, Query

from app.models.database import (
    add_seed_location,
    get_search_candidates,
    list_seed_locations,
    list_seed_searches,
    set_seed_location_active,
)
from app.services.seed_queue import (
    get_queue_status,
    pause_queue,
    resume_queue,
    retry_failed,
    start_queue,
)


router = APIRouter()


@router.get("/status")
def status():
    return get_queue_status()


@router.post("/start")
def start(
    search_term: str | None = Query(None),
    country_code: str | None = Query(None, min_length=2, max_length=2),
    limit: int = Query(200, ge=1, le=500),
    interval_seconds: int = Query(300, ge=30, le=86400),
):
    term = search_term or config("DIRECTORY_SEARCH_TERM", default="restaurantes")
    return start_queue(term, country_code, limit, interval_seconds)


@router.post("/pause")
def pause():
    return pause_queue()


@router.post("/resume")
def resume():
    return resume_queue()


@router.post("/retry-failed")
def retry():
    return retry_failed()


@router.get("/locations")
def locations(country_code: str | None = None):
    return {"locations": list_seed_locations(country_code)}


@router.post("/locations")
def add_location(country_code: str, name: str, region: str | None = None):
    return add_seed_location(country_code, name, region, tier="manual")


@router.patch("/locations/{location_id}")
def toggle_location(location_id: int, active: bool):
    return set_seed_location_active(location_id, active)


@router.get("/searches")
def searches(search_term: str | None = None):
    return {"searches": list_seed_searches(search_term)}


@router.get("/searches/{search_id}/candidates")
def candidates(search_id: int):
    return {"candidates": get_search_candidates(search_id)}
