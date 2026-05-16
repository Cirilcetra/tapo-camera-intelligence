"""
Unified event pipeline.

Both the pytapo poller (native camera events) and the OpenCV motion detector
route through this single entry point so downstream handling (snapshot, DB
write, WebSocket broadcast, future AI hooks) is identical regardless of source.

`handle_event` is designed to be called from any thread or asyncio context:
  - From RTSPWorker threads (via motion_detector) it is invoked synchronously.
  - From TapoPoller asyncio tasks it is awaited as a coroutine.

The function is deliberately simple — any AI inference (YOLO, caption) should
be added inside the `_run_ai_hooks` stub before the event is published.
"""

import logging
from typing import Callable, Optional

import numpy as np

from app.ai.snapshot_capture import save_snapshot
from app.services.event_service import publish_event_from_thread

logger = logging.getLogger(__name__)


def _run_ai_hooks(camera_id: int, event_type: str, frame: Optional[np.ndarray]) -> Optional[str]:
    """
    Hook point for future AI inference (YOLO, LLM caption, etc.).

    Returns an ai_summary string, or None if no inference was run.
    Add YOLO / vision-API calls here in Phase 3+.
    """
    return None


def handle_event(
    camera_id: int,
    event_type: str,
    frame_provider: Callable[[], Optional[np.ndarray]],
) -> None:
    """
    Process a single detection event end-to-end.

    Parameters
    ----------
    camera_id:
        DB id of the originating camera.
    event_type:
        Human-readable label: "motion", "person", "vehicle", "pet", etc.
    frame_provider:
        Zero-argument callable that returns the most recent frame (numpy array)
        or None if no frame is available.  Called once here — no frame is
        captured before the event is confirmed.

    This function is synchronous and safe to call from background threads.
    """
    frame = frame_provider()

    snapshot_path: Optional[str] = None
    if frame is not None:
        try:
            snapshot_path = save_snapshot(camera_id, frame)
        except Exception as exc:
            logger.error("event_pipeline: snapshot failed for cam_%d: %s", camera_id, exc)

    ai_summary: Optional[str] = None
    try:
        ai_summary = _run_ai_hooks(camera_id, event_type, frame)
    except Exception as exc:
        logger.error("event_pipeline: AI hook error for cam_%d: %s", camera_id, exc)

    publish_event_from_thread(camera_id, event_type, snapshot_path, ai_summary=ai_summary)
