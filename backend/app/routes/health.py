from fastapi import APIRouter
from app.streaming.stream_manager import stream_manager

router = APIRouter()


@router.get("/api/health")
async def health():
    return {
        "status": "ok",
        "cameras_active": stream_manager.active_count(),
    }
