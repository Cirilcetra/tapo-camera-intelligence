import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.events.event_bus import event_bus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    await websocket.accept()
    q = event_bus.subscribe()
    logger.info("WS /ws/events: client connected")

    try:
        while True:
            try:
                # Wait up to 30s for an event; send a heartbeat if idle
                event_data = await asyncio.wait_for(q.get(), timeout=30.0)
                await websocket.send_text(json.dumps(event_data))
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        logger.info("WS /ws/events: client disconnected")
    except Exception as exc:
        logger.error("WS /ws/events: error: %s", exc)
    finally:
        event_bus.unsubscribe(q)
