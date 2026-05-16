import logging
from typing import List

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.models.event import Event
from app.schemas.event import EventSearchResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["search"])


@router.get("/search", response_model=List[EventSearchResult])
async def semantic_search(
    q: str = Query(..., min_length=1, description="Natural-language search query"),
    top_k: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.2, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """
    Embed the query and return events ranked by cosine similarity.
    Returns an empty list (not an error) if no API key is configured
    or if the index is empty.
    """
    from app.ai.openai_client import get_embedding
    from app.ai.semantic_search import semantic_index
    from app.config import settings

    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Semantic search requires OPENAI_API_KEY to be configured.",
        )

    if semantic_index.size() == 0:
        return []

    vec = await get_embedding(q)
    if vec is None:
        raise HTTPException(
            status_code=502,
            detail="Failed to embed query. OpenAI may be unavailable.",
        )

    query_arr = np.array(vec, dtype=np.float32)
    ranked = semantic_index.search(query_arr, top_k=top_k, min_score=min_score)

    if not ranked:
        return []

    event_ids = [eid for eid, _ in ranked]
    scores = {eid: score for eid, score in ranked}

    events = db.query(Event).filter(Event.id.in_(event_ids)).all()
    events_by_id = {e.id: e for e in events}

    results: List[EventSearchResult] = []
    for event_id in event_ids:
        ev = events_by_id.get(event_id)
        if ev is None:
            continue
        results.append(
            EventSearchResult(
                id=ev.id,
                camera_id=ev.camera_id,
                type=ev.type,
                snapshot_path=ev.snapshot_path,
                ai_summary=ev.ai_summary,
                enrichment_status=ev.enrichment_status,
                timestamp=ev.timestamp,
                acknowledged=ev.acknowledged,
                score=scores[event_id],
            )
        )

    return results
