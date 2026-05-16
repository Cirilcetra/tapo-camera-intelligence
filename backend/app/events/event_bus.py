import asyncio
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class EventBus:
    """
    In-process asyncio fan-out bus.

    All messages sent to subscribers are wrapped in a typed envelope:
        {"type": "<event_type>", "data": {...}}

    Worker threads push events via push_from_thread() (type = "event_created").
    The enricher calls publish_typed() with type = "event_updated".
    WebSocket handlers subscribe/unsubscribe asyncio.Queue instances.
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        logger.debug("EventBus: subscriber added (%d total)", len(self._subscribers))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)
        logger.debug("EventBus: subscriber removed (%d total)", len(self._subscribers))

    async def publish_typed(self, msg_type: str, data: dict) -> None:
        """Publish a typed envelope from async context."""
        envelope = {"type": msg_type, "data": data}
        dead = set()
        for q in self._subscribers:
            try:
                q.put_nowait(envelope)
            except asyncio.QueueFull:
                logger.warning("EventBus: subscriber queue full, dropping %s", msg_type)
            except Exception as exc:
                logger.error("EventBus: publish error: %s", exc)
                dead.add(q)
        for q in dead:
            self._subscribers.discard(q)

    async def publish(self, event_data: dict) -> None:
        """Publish an event_created envelope from async context (legacy alias)."""
        await self.publish_typed("event_created", event_data)

    def push_from_thread(self, event_data: dict) -> None:
        """Thread-safe publish (event_created) called from worker threads."""
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(
            asyncio.ensure_future,
            self.publish(event_data),
        )


event_bus = EventBus()
