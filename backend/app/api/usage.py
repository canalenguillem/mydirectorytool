from fastapi import APIRouter, Query

from app.services.openai_usage import get_usage_summary


router = APIRouter()


@router.get("/summary")
def usage_summary(days: int = Query(30, ge=1, le=3650)):
    return get_usage_summary(days)
