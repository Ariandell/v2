"""Health-check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def health_check():
    return {"status": "online", "models_loaded": True}
