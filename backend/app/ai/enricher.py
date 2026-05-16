"""
EventEnricher — asynchronous AI enrichment pipeline.

For each event id that enters the queue:
  1. Load the event row + resolve the snapshot path.
  2. Downscale the snapshot to max 768px on the long edge and base64-encode.
  3. Call OpenAI Vision → ai_summary.
  4. Embed the summary → float32 vector → store as bytes.
  5. Update the events row (ai_summary, embedding, enrichment_status).
  6. Push an `event_updated` message to the event bus.
  7. Register the vector in the SemanticIndex.

Errors are caught per-event; a failure writes enrichment_status='failed'
and still emits event_updated so the UI can reflect the final state.

Thread → asyncio handoff
------------------------
Worker threads (rtsp_worker) call `enqueue_from_thread(event_id)`.
That uses `loop.call_soon_threadsafe(queue.put_nowait, event_id)` to safely
schedule the put from outside the event loop.
"""
import asyncio
import base64
import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

_QUEUE_MAXSIZE = 200


class EventEnricher:
    def __init__(self):
        self._queue: asyncio.Queue[int] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._tasks: list[asyncio.Task] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        if not settings.AI_ENRICHMENT_ENABLED:
            logger.info("EventEnricher: disabled (AI_ENRICHMENT_ENABLED=false)")
            return
        if not settings.OPENAI_API_KEY:
            logger.warning("EventEnricher: OPENAI_API_KEY not set — enrichment will be skipped")
        concurrency = max(1, settings.AI_ENRICHMENT_CONCURRENCY)
        for i in range(concurrency):
            task = asyncio.create_task(self._worker(i), name=f"enricher-{i}")
            self._tasks.append(task)
        logger.info("EventEnricher: started %d worker(s)", concurrency)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("EventEnricher: stopped")

    # ------------------------------------------------------------------
    # Public enqueue
    # ------------------------------------------------------------------

    def enqueue_from_thread(self, event_id: int) -> None:
        """Called from a worker thread to schedule enrichment."""
        if not settings.AI_ENRICHMENT_ENABLED:
            return
        if self._loop is None or self._loop.is_closed():
            return
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event_id)
        except asyncio.QueueFull:
            logger.warning("EventEnricher: queue full, dropping event_id=%d", event_id)

    async def enqueue(self, event_id: int) -> None:
        """Called from async context (backfill route)."""
        if not settings.AI_ENRICHMENT_ENABLED:
            return
        try:
            self._queue.put_nowait(event_id)
        except asyncio.QueueFull:
            logger.warning("EventEnricher: queue full, dropping event_id=%d", event_id)

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    async def _worker(self, worker_id: int) -> None:
        logger.debug("EventEnricher worker-%d: running", worker_id)
        while True:
            event_id = await self._queue.get()
            try:
                await self._process(event_id)
            except Exception as exc:
                logger.error("EventEnricher worker-%d: unhandled error for event %d: %s", worker_id, event_id, exc)
            finally:
                self._queue.task_done()

    # ------------------------------------------------------------------
    # Core enrichment
    # ------------------------------------------------------------------

    async def _process(self, event_id: int) -> None:
        from app.database import SessionLocal
        from app.models.event import Event
        from app.ai.openai_client import get_vision_summary, get_embedding
        from app.events.event_bus import event_bus
        from app.ai.semantic_search import semantic_index

        db = SessionLocal()
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                logger.warning("EventEnricher: event %d not found", event_id)
                return

            if event.enrichment_status == "done":
                logger.debug("EventEnricher: event %d already done, skipping", event_id)
                return

            # --- resolve snapshot ------------------------------------------
            image_b64 = await self._load_snapshot_b64(event.snapshot_path)

            # --- vision summary --------------------------------------------
            summary: Optional[str] = None
            embedding_bytes: Optional[bytes] = None
            status = "failed"

            if image_b64:
                summary = await get_vision_summary(image_b64)

            if summary:
                vec = await get_embedding(summary)
                if vec:
                    arr = np.array(vec, dtype=np.float32)
                    embedding_bytes = arr.tobytes()
                    status = "done"
                    semantic_index.add(event_id, arr)
            elif not image_b64:
                # No snapshot — skip but mark as done so we don't retry forever
                status = "skipped"
                summary = None

            # --- persist ---------------------------------------------------
            event.ai_summary = summary
            event.embedding = embedding_bytes
            event.enrichment_status = status
            db.commit()
            db.refresh(event)

            logger.info(
                "EventEnricher: event %d enriched status=%s summary=%s",
                event_id,
                status,
                repr(summary[:60]) if summary else None,
            )

            # --- broadcast event_updated to WS clients ---------------------
            event_dict = {
                "id": event.id,
                "camera_id": event.camera_id,
                "type": event.type,
                "snapshot_path": event.snapshot_path,
                "ai_summary": event.ai_summary,
                "enrichment_status": event.enrichment_status,
                "timestamp": event.timestamp.isoformat(),
                "acknowledged": event.acknowledged,
            }
            await event_bus.publish_typed("event_updated", event_dict)

        except Exception as exc:
            logger.error("EventEnricher: error processing event %d: %s", event_id, exc)
            db.rollback()
            # Attempt to mark as failed
            try:
                event = db.query(Event).filter(Event.id == event_id).first()
                if event:
                    event.enrichment_status = "failed"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    async def _load_snapshot_b64(self, snapshot_path: Optional[str]) -> Optional[str]:
        """Load and downscale snapshot to max 768px, return base64 string."""
        if not snapshot_path:
            return None
        full_path = Path(settings.SNAPSHOT_DIR) / snapshot_path
        if not full_path.exists():
            logger.warning("EventEnricher: snapshot not found: %s", full_path)
            return None
        try:
            img = Image.open(full_path).convert("RGB")
            # Downscale so the long edge is at most 768px
            max_dim = 768
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception as exc:
            logger.error("EventEnricher: failed to load snapshot %s: %s", snapshot_path, exc)
            return None


# Module-level singleton
event_enricher = EventEnricher()
