import logging
import time
from typing import Dict, Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 3.0


class MotionDetector:
    """
    Per-camera background-subtraction motion detector.

    Uses MOG2 (Mixture of Gaussians) for robust background modeling.
    A per-camera cooldown prevents event spam — only one event fires
    every COOLDOWN_SECONDS per camera.
    """

    def __init__(self):
        # camera_id -> cv2.BackgroundSubtractor
        self._subtractors: Dict[int, cv2.BackgroundSubtractorMOG2] = {}
        # camera_id -> last event unix timestamp
        self._last_event_time: Dict[int, float] = {}

    def _get_subtractor(self, camera_id: int) -> cv2.BackgroundSubtractorMOG2:
        if camera_id not in self._subtractors:
            self._subtractors[camera_id] = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=16, detectShadows=False
            )
        return self._subtractors[camera_id]

    def process_frame(self, camera_id: int, frame) -> None:
        """
        Called synchronously from the RTSPWorker thread for each sampled frame.
        If motion exceeds threshold and cooldown has elapsed, fires an event.
        """
        subtractor = self._get_subtractor(camera_id)

        # Downscale for speed, apply blur to reduce noise
        small = cv2.resize(frame, (640, 360))
        blurred = cv2.GaussianBlur(small, (5, 5), 0)
        fg_mask = subtractor.apply(blurred)

        motion_score = int(cv2.countNonZero(fg_mask))

        if motion_score < settings.MOTION_THRESHOLD:
            return

        now = time.monotonic()
        last = self._last_event_time.get(camera_id, 0.0)
        if (now - last) < COOLDOWN_SECONDS:
            return

        self._last_event_time[camera_id] = now
        logger.info(
            "MotionDetector: motion on cam_%d score=%d — firing event",
            camera_id,
            motion_score,
        )
        self._fire_event(camera_id, frame)

    def _fire_event(self, camera_id: int, frame) -> None:
        from app.events.event_pipeline import handle_event

        handle_event(camera_id, "motion", lambda: frame)

    def reset(self, camera_id: int) -> None:
        """Remove state for a camera (called on camera delete)."""
        self._subtractors.pop(camera_id, None)
        self._last_event_time.pop(camera_id, None)


motion_detector = MotionDetector()
