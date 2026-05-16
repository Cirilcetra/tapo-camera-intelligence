from fastapi import APIRouter
from pydantic import BaseModel
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsRead(BaseModel):
    snapshot_dir: str
    motion_threshold: int
    frame_skip: int
    mediamtx_url: str


class SettingsUpdate(BaseModel):
    motion_threshold: int | None = None
    frame_skip: int | None = None


@router.get("", response_model=SettingsRead)
def get_settings():
    return SettingsRead(
        snapshot_dir=settings.SNAPSHOT_DIR,
        motion_threshold=settings.MOTION_THRESHOLD,
        frame_skip=settings.FRAME_SKIP,
        mediamtx_url=settings.MEDIAMTX_URL,
    )


@router.put("")
def update_settings(body: SettingsUpdate):
    """
    Persist mutable settings at runtime.
    Only motion_threshold and frame_skip are writable; storage paths are
    env-only and read-only from the UI.
    """
    if body.motion_threshold is not None:
        settings.MOTION_THRESHOLD = body.motion_threshold
    if body.frame_skip is not None:
        settings.FRAME_SKIP = body.frame_skip
    return get_settings()
