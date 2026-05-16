import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.event import Event
from app.schemas.event import EventAck, EventRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/enrich-missing", status_code=202)
async def enrich_missing(db: Session = Depends(get_db)):
    """
    Re-queue all events where enrichment_status is not 'done' so they can be
    processed by the enricher. Returns the count of events queued.
    """
    from app.ai.enricher import event_enricher

    events = (
        db.query(Event)
        .filter(Event.enrichment_status != "done")
        .all()
    )
    count = 0
    for event in events:
        await event_enricher.enqueue(event.id)
        count += 1

    logger.info("enrich_missing: queued %d events", count)
    return {"queued": count}


@router.get("", response_model=List[EventRead])
def list_events(
    camera_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Event)
    if camera_id is not None:
        q = q.filter(Event.camera_id == camera_id)
    if type is not None:
        q = q.filter(Event.type == type)
    if since is not None:
        q = q.filter(Event.timestamp >= since)
    if until is not None:
        q = q.filter(Event.timestamp <= until)
    return q.order_by(Event.timestamp.desc()).limit(limit).all()


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/snapshot")
def get_snapshot(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or not event.snapshot_path:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    full_path = Path(settings.SNAPSHOT_DIR) / event.snapshot_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot file missing")
    return FileResponse(str(full_path), media_type="image/jpeg")


@router.patch("/{event_id}/ack", response_model=EventRead)
def acknowledge_event(event_id: int, body: EventAck, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.acknowledged = body.acknowledged
    db.commit()
    db.refresh(event)
    return event
