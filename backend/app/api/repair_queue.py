from fastapi import APIRouter, Query

from app.services.repair_queue import (
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
    limit: int = Query(3, ge=1, le=500),
    interval_seconds: int = Query(300, ge=60, le=86400),
):
    return start_queue(limit, interval_seconds)


@router.post("/pause")
def pause():
    return pause_queue()


@router.post("/resume")
def resume():
    return resume_queue()


@router.post("/retry-failed")
def retry():
    return retry_failed()
