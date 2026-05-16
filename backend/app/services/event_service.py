import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.event import Event

logger = logging.getLogger(__name__)


def create_event_sync(
    camera_id: int,
    event_type: str,
    snapshot_path: Optional[str],
    ai_summary: Optional[str] = None,
) -> dict:
    """
    Insert an event row into the DB (synchronous, called from worker thread).
    Returns a dict suitable for the event bus.
    """
    db: Session = SessionLocal()
    try:
        event = Event(
            camera_id=camera_id,
            type=event_type,
            snapshot_path=snapshot_path,
            ai_summary=ai_summary,
            acknowledged=False,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

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
        logger.info(
            "EventService: created %s event id=%d for cam_%d",
            event_type,
            event.id,
            camera_id,
        )
        return event_dict
    except Exception as exc:
        logger.error("EventService: DB error: %s", exc)
        db.rollback()
        return {}
    finally:
        db.close()


def publish_event_from_thread(
    camera_id: int,
    event_type: str,
    snapshot_path: Optional[str],
    ai_summary: Optional[str] = None,
) -> None:
    """Called from worker threads or async tasks. Creates DB row, pushes to event bus, queues enrichment."""
    from app.events.event_bus import event_bus
    from app.ai.enricher import event_enricher

    event_dict = create_event_sync(camera_id, event_type, snapshot_path, ai_summary=ai_summary)
    if event_dict:
        event_bus.push_from_thread(event_dict)
        event_enricher.enqueue_from_thread(event_dict["id"])
