"""
Per-camera asyncio poller that calls TapoClient.get_events() on a fixed
interval and fires a callback for every new event that has not been seen
before.

Deduplication is done by (start_ts, type) so events are never double-fired
even if they appear in consecutive poll windows.  The poller advances the
lower bound of its query window after each successful poll to avoid
re-scanning stale history.

Backoff: on consecutive errors the poll interval is doubled up to
MAX_BACKOFF_SECONDS before resetting on the next success.
"""

import asyncio
import logging
import time
from typing import Callable, Awaitable, Optional, Set, Tuple

from app.integrations.tapo_client import TapoClient

logger = logging.getLogger(__name__)

MAX_BACKOFF_SECONDS = 60.0


class TapoPoller:
    """
    Polls a single Tapo camera for detection events via pytapo's getEvents.

    Parameters
    ----------
    camera_id:
        DB id of the camera — passed through to the callback.
    tapo_client:
        Already-authenticated TapoClient instance.
    on_event:
        Async callback `(camera_id: int, event_type: str, start_ts: int) -> None`.
        Called from the poller's asyncio task — no need for thread safety.
    on_status_change:
        Sync callback `(camera_id: int, status: str) -> None` — mirrors the
        signature used by RTSPWorker so StreamManager can re-use the same handler.
    poll_interval:
        How often to poll (seconds).  Defaults to settings.TAPO_POLL_INTERVAL.
    lookback_seconds:
        On first poll, how far back to search for events.
        Defaults to settings.TAPO_EVENT_LOOKBACK_SECONDS.
    """

    def __init__(
        self,
        camera_id: int,
        tapo_client: TapoClient,
        on_event: Callable[[int, str, int], Awaitable[None]],
        on_status_change: Callable[[int, str], None],
        poll_interval: Optional[float] = None,
        lookback_seconds: Optional[int] = None,
    ):
        from app.config import settings

        self.camera_id = camera_id
        self.tapo_client = tapo_client
        self.on_event = on_event
        self.on_status_change = on_status_change
        self.poll_interval = poll_interval if poll_interval is not None else settings.TAPO_POLL_INTERVAL
        self.lookback_seconds = (
            lookback_seconds if lookback_seconds is not None else settings.TAPO_EVENT_LOOKBACK_SECONDS
        )

        # Tracks (start_ts, type) pairs we have already fired so we don't
        # double-emit if they appear in overlapping query windows.
        self._seen: Set[Tuple[int, str]] = set()

        # Lower bound for the next getEvents query window.
        # Starts at (now - lookback_seconds) and advances after each poll.
        self._last_end_ts: int = int(time.time()) - self.lookback_seconds

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._consecutive_errors = 0
        self._camera_online: Optional[bool] = None  # tracks last reported status

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background polling task."""
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.ensure_future(self._run())
        logger.info("TapoPoller cam_%d: started (interval=%.1fs)", self.camera_id, self.poll_interval)

    async def stop(self) -> None:
        """Signal the poller to stop and wait for the task to finish."""
        self._stop_event.set()
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=self.poll_interval + 2)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        logger.info("TapoPoller cam_%d: stopped", self.camera_id)

    # ------------------------------------------------------------------
    # Internal polling loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._poll_once()
                self._consecutive_errors = 0
                self._set_online(True)
            except Exception as exc:
                self._consecutive_errors += 1
                self._set_online(False)
                backoff = min(
                    self.poll_interval * (2 ** min(self._consecutive_errors, 6)),
                    MAX_BACKOFF_SECONDS,
                )
                logger.warning(
                    "TapoPoller cam_%d: poll error #%d — %s — backing off %.0fs",
                    self.camera_id,
                    self._consecutive_errors,
                    exc,
                    backoff,
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
                except asyncio.TimeoutError:
                    pass
                continue

            # Normal sleep between polls
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                pass

    async def _poll_once(self) -> None:
        now = int(time.time())
        # Add a 5-second look-ahead so very recent events aren't missed.
        end_ts = now + 5

        events = await self.tapo_client.get_events(self._last_end_ts, end_ts)

        new_events = []
        for ev in events:
            key = (ev["start_ts"], ev["type"])
            if key not in self._seen:
                self._seen.add(key)
                new_events.append(ev)

        if new_events:
            logger.info(
                "TapoPoller cam_%d: %d new event(s) in window [%d, %d]",
                self.camera_id,
                len(new_events),
                self._last_end_ts,
                end_ts,
            )

        for ev in new_events:
            try:
                await self.on_event(self.camera_id, ev["type"], ev["start_ts"])
            except Exception as exc:
                logger.error(
                    "TapoPoller cam_%d: on_event callback error: %s", self.camera_id, exc
                )

        # Advance window; keep a 10-second overlap to handle late-arriving events.
        overlap = 10
        self._last_end_ts = max(self._last_end_ts, end_ts - overlap)

        # Prune the seen-set to avoid unbounded growth.
        # Keep only events within the current window so dedup still works.
        cutoff = self._last_end_ts - overlap
        self._seen = {(ts, t) for (ts, t) in self._seen if ts >= cutoff}

    def _set_online(self, online: bool) -> None:
        """Report status change only when it actually changes."""
        if self._camera_online is online:
            return
        self._camera_online = online
        status = "online" if online else "offline"
        try:
            self.on_status_change(self.camera_id, status)
        except Exception as exc:
            logger.error("TapoPoller cam_%d: on_status_change error: %s", self.camera_id, exc)
