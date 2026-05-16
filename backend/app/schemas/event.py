from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EventRead(BaseModel):
    id: int
    camera_id: int
    type: str
    snapshot_path: Optional[str] = None
    ai_summary: Optional[str] = None
    enrichment_status: Optional[str] = None
    timestamp: datetime
    acknowledged: bool

    model_config = {"from_attributes": True}


class EventSearchResult(EventRead):
    score: float


class EventAck(BaseModel):
    acknowledged: bool = True
