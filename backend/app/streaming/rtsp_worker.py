import asyncio
import logging
import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

RECONNECT_DELAY = 5   # seconds between reconnect attempts
MAX_RECONNECT_DELAY = 60


class RTSPWorker:
    """
    Per-camera worker thread that reads frames from MediaMTX's RTSP republish
    endpoint and feeds them into the motion detection pipeline.

    The worker also caches the most recent decoded frame in `_latest_frame`
    so that the TapoPoller can grab a snapshot at the moment a native camera
    event fires without opening a second RTSP session.

    When `motion_detection_enabled` is False (set by StreamManager after a
    successful pytapo probe), the `on_frame` callback is skipped and OpenCV
    motion detection is effectively disabled for this camera.  The worker
    keeps reading frames so the MediaMTX HLS stream stays alive and the
    latest-frame cache stays fresh.
    """

    def __init__(
        self,
        camera_id: int,
        on_frame: Callable[[int, object], None],
        on_status_change: Callable[[int, str], None],
    ):
        self.camera_id = camera_id
        self.on_frame = on_frame
        self.on_status_change = on_status_change
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Latest decoded frame — written by the worker thread, read by poller.
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        # When False, the on_frame (OpenCV motion) callback is bypassed.
        self.motion_detection_enabled: bool = True

    @property
    def rtsp_url(self) -> str:
        return f"{settings.MEDIAMTX_RTSP_URL}/cam_{self.camera_id}"

    # ------------------------------------------------------------------
    # Latest-frame access (thread-safe)
    # ------------------------------------------------------------------

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Return a copy of the most recently decoded frame, or None if no frame
        has been decoded yet.  Thread-safe.
        """
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"rtsp_worker_{self.camera_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("RTSPWorker cam_%d started", self.camera_id)

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("RTSPWorker cam_%d stopped", self.camera_id)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run(self):
        reconnect_delay = RECONNECT_DELAY
        frame_skip = settings.FRAME_SKIP
        frame_count = 0

        while not self._stop_event.is_set():
            logger.info("RTSPWorker cam_%d connecting to %s", self.camera_id, self.rtsp_url)
            cap = cv2.VideoCapture(self.rtsp_url)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10_000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10_000)

            if not cap.isOpened():
                logger.warning(
                    "RTSPWorker cam_%d: could not open stream, retrying in %ds",
                    self.camera_id,
                    reconnect_delay,
                )
                self.on_status_change(self.camera_id, "offline")
                self._stop_event.wait(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)
                continue

            self.on_status_change(self.camera_id, "online")
            reconnect_delay = RECONNECT_DELAY
            logger.info("RTSPWorker cam_%d: stream open", self.camera_id)

            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning("RTSPWorker cam_%d: read failed — reconnecting", self.camera_id)
                    break

                # Always cache the latest frame for snapshot grabs.
                with self._frame_lock:
                    self._latest_frame = frame.copy()

                frame_count += 1
                if frame_count % frame_skip != 0:
                    continue

                # Only run OpenCV motion detection when not superseded by pytapo.
                if self.motion_detection_enabled:
                    try:
                        self.on_frame(self.camera_id, frame)
                    except Exception as exc:
                        logger.error("RTSPWorker cam_%d on_frame error: %s", self.camera_id, exc)

            cap.release()
            if not self._stop_event.is_set():
                self.on_status_change(self.camera_id, "offline")
                self._stop_event.wait(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)

        self.on_status_change(self.camera_id, "offline")
