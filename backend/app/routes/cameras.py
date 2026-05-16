import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraRead, CameraTest
from app.services.camera_service import create_camera, test_rtsp_connection
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cameras", tags=["cameras"])


# ------------------------------------------------------------------
# Control request / response schemas
# ------------------------------------------------------------------

class ControlsUpdate(BaseModel):
    motion_detection: Optional[bool] = None
    privacy_mode: Optional[bool] = None
    led: Optional[bool] = None


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------

@router.get("", response_model=List[CameraRead])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
async def add_camera(body: CameraCreate, db: Session = Depends(get_db)):
    camera = create_camera(
        db,
        name=body.name,
        ip=body.ip,
        username=body.username,
        password=body.password,
        rtsp_path=body.rtsp_path,
        preferred_provider=body.preferred_provider,
        auth_method=body.auth_method,
    )

    from app.streaming.stream_manager import stream_manager

    try:
        await stream_manager.start(camera)
    except RuntimeError as exc:
        # Probe/start failed — roll back the camera row.
        db.delete(camera)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # Refresh so provider column set by stream_manager is visible.
    db.refresh(camera)
    return camera


@router.get("/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    from app.streaming.stream_manager import stream_manager

    # stream_manager.stop() handles both RTSP worker shutdown and MediaMTX path removal.
    await stream_manager.stop(camera_id)

    db.delete(camera)
    db.commit()


@router.get("/{camera_id}/stream")
def get_stream_url(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    from app.streaming.stream_manager import StreamManager

    if not StreamManager.camera_needs_rtsp(camera):
        return {
            "hls_url": None,
            "camera_id": camera_id,
            "reason": "cloud_account_no_rtsp",
        }

    hls_url = f"{settings.MEDIAMTX_URL}/cam_{camera_id}/index.m3u8"
    return {"hls_url": hls_url, "camera_id": camera_id}


@router.get("/{camera_id}/status")
def get_camera_status(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"camera_id": camera_id, "status": camera.status, "provider": camera.provider}


# ------------------------------------------------------------------
# Connection test — also probes pytapo
# ------------------------------------------------------------------

@router.post("/test")
async def test_camera_connection(body: CameraTest):
    preferred = body.preferred_provider
    auth_method = body.auth_method

    # RTSP connection check.
    # Note: RTSP requires the camera-account credentials. If the user picked
    # cloud_account auth, the supplied creds likely won't authenticate RTSP.
    # We still attempt it so the user gets a clear signal.
    rtsp_ok = await test_rtsp_connection(
        ip=body.ip,
        username=body.username,
        password=body.password,
        rtsp_path=body.rtsp_path,
    )

    # For cloud_account mode, RTSP failure is *expected* if camera-account isn't
    # also set up — we don't gate the test on RTSP in that case.
    if not rtsp_ok and auth_method == "camera_account":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not connect to RTSP stream. Check IP and credentials.",
        )

    # pytapo probe — behaviour depends on preferred_provider.
    tapo_supported = False
    if preferred != "rtsp":
        try:
            from app.integrations.tapo_client import TapoClient
            client = TapoClient(
                host=body.ip,
                username=body.username,
                password=body.password,
                auth_method=auth_method,
            )
            tapo_supported = await client.probe()
        except Exception as exc:
            logger.debug("test_camera_connection: pytapo probe error: %s", exc)

        if preferred == "tapo" and not tapo_supported:
            hint = (
                "Check Tapo email/password."
                if auth_method == "cloud_account"
                else "Check camera-account credentials, or switch to RTSP mode."
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Tapo API authentication failed. {hint}",
            )

    mode_label = {
        "tapo": "Tapo native events",
        "rtsp": "RTSP / OpenCV motion",
        "auto": "Tapo native events" if tapo_supported else "RTSP / OpenCV motion (Tapo not available)",
    }[preferred]

    return {
        "success": True,
        "message": "Connection successful",
        "tapo_supported": tapo_supported,
        "rtsp_supported": rtsp_ok,
        "mode": mode_label,
    }


# ------------------------------------------------------------------
# pytapo-specific endpoints (Tapo cameras only)
# ------------------------------------------------------------------

def _get_tapo_client(camera_id: int, db: Session):
    """Return the active TapoClient for camera_id or raise 422."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if camera.provider != "tapo":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Camera is not using the pytapo provider. Native controls unavailable.",
        )
    from app.streaming.stream_manager import stream_manager
    client = stream_manager.get_tapo_client(camera_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TapoClient not initialised for this camera. Is the camera online?",
        )
    return client


@router.get("/{camera_id}/info")
async def get_camera_info(camera_id: int, db: Session = Depends(get_db)):
    """Return raw device info from the Tapo camera API."""
    client = _get_tapo_client(camera_id, db)
    try:
        info = await client.get_basic_info()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"pytapo error: {exc}",
        )
    return info


@router.get("/{camera_id}/controls")
async def get_camera_controls(camera_id: int, db: Session = Depends(get_db)):
    """
    Return current motion-detection and privacy-mode state from the camera.
    """
    client = _get_tapo_client(camera_id, db)
    try:
        controls = await client.get_controls()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"pytapo error: {exc}",
        )
    return controls


@router.patch("/{camera_id}/controls")
async def update_camera_controls(
    camera_id: int,
    body: ControlsUpdate,
    db: Session = Depends(get_db),
):
    """
    Toggle motion detection, privacy mode, and/or LED on a Tapo camera.
    Only fields explicitly set in the request body are changed.
    """
    client = _get_tapo_client(camera_id, db)
    errors: Dict[str, str] = {}

    if body.motion_detection is not None:
        try:
            await client.set_motion_detection(body.motion_detection)
        except Exception as exc:
            errors["motion_detection"] = str(exc)

    if body.privacy_mode is not None:
        try:
            await client.set_privacy_mode(body.privacy_mode)
        except Exception as exc:
            errors["privacy_mode"] = str(exc)

    if body.led is not None:
        try:
            await client.set_led(body.led)
        except Exception as exc:
            errors["led"] = str(exc)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "Some controls failed to update", "errors": errors},
        )

    return {"success": True, "updated": body.model_dump(exclude_none=True)}
