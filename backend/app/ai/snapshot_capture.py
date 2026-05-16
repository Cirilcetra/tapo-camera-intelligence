import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import cv2

from app.config import settings

logger = logging.getLogger(__name__)


def save_snapshot(camera_id: int, frame) -> str:
    """
    Save a frame as JPEG to media/snapshots/{camera_id}/{ISO-timestamp}.jpg.
    Returns the relative path from the snapshot root.
    """
    snap_root = Path(settings.SNAPSHOT_DIR)
    cam_dir = snap_root / str(camera_id)
    cam_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"{ts}.jpg"
    full_path = cam_dir / filename

    success = cv2.imwrite(str(full_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not success:
        logger.error("snapshot_capture: failed to write %s", full_path)
        return ""

    # Return path relative to snapshot root for storage in DB
    rel_path = f"{camera_id}/{filename}"
    logger.debug("snapshot_capture: saved %s", rel_path)
    return rel_path
