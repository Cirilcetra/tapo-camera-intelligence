import asyncio
import logging
from typing import Dict, Optional

from app.streaming.rtsp_worker import RTSPWorker

logger = logging.getLogger(__name__)


class StreamManager:
    def __init__(self):
        self._workers: Dict[int, RTSPWorker] = {}
        self._pollers: Dict[int, object] = {}  # camera_id -> TapoPoller
        self._tapo_clients: Dict[int, object] = {}  # camera_id -> TapoClient
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Helpers called from the motion detector / RTSP worker
    # ------------------------------------------------------------------

    def _on_frame(self, camera_id: int, frame) -> None:
        """Called from the worker thread for every processed frame (OpenCV path)."""
        from app.ai.motion_detector import motion_detector
        motion_detector.process_frame(camera_id, frame)

    def _on_status_change(self, camera_id: int, new_status: str) -> None:
        """Called from worker threads or the TapoPoller when stream status changes."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(
            asyncio.ensure_future,
            self._update_camera_status(camera_id, new_status),
        )

    async def _update_camera_status(self, camera_id: int, new_status: str) -> None:
        from app.database import SessionLocal
        from app.models.camera import Camera

        db = SessionLocal()
        try:
            cam = db.query(Camera).filter(Camera.id == camera_id).first()
            if cam:
                cam.status = new_status
                db.commit()
        except Exception as exc:
            logger.error("Status update error for cam_%d: %s", camera_id, exc)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # pytapo event callback (async, called from TapoPoller)
    # ------------------------------------------------------------------

    async def _on_tapo_event(self, camera_id: int, event_type: str, start_ts: int) -> None:
        """
        Called by TapoPoller when a native camera event arrives.
        Grabs the latest RTSP frame (if any) and routes through event_pipeline.
        """
        from app.events.event_pipeline import handle_event

        worker = self._workers.get(camera_id)
        frame_provider = worker.get_latest_frame if worker else lambda: None

        # handle_event is synchronous; run in thread to avoid blocking.
        await asyncio.to_thread(handle_event, camera_id, event_type, frame_provider)

    # ------------------------------------------------------------------
    # pytapo probe + poller management
    # ------------------------------------------------------------------

    async def _try_start_tapo(self, camera) -> bool:
        """
        Attempt to activate pytapo for a camera based on its preferred_provider.

        preferred_provider behaviour:
          "rtsp"  → skip entirely; always return False (use OpenCV)
          "tapo"  → probe required; raise RuntimeError if it fails (user chose Tapo explicitly)
          "auto"  → probe; return False silently on failure (fall back to OpenCV)

        Returns True if pytapo is now active, False if OpenCV should be used.
        """
        from app.integrations.tapo_client import TapoClient
        from app.integrations.tapo_poller import TapoPoller
        from app.services.crypto import decrypt_password

        camera_id = camera.id
        preferred = getattr(camera, "preferred_provider", "auto")

        # User explicitly chose RTSP — skip pytapo entirely.
        if preferred == "rtsp":
            logger.info("StreamManager cam_%d: preferred_provider=rtsp — skipping pytapo", camera_id)
            return False

        password = decrypt_password(camera.password_encrypted)
        client = TapoClient(
            host=camera.ip,
            username=camera.username,
            password=password,
            auth_method=getattr(camera, "auth_method", "camera_account"),
        )

        logger.info(
            "StreamManager cam_%d: probing via pytapo (preferred=%s) …", camera_id, preferred
        )
        try:
            ok = await client.probe()
        except Exception as exc:
            ok = False
            logger.warning("StreamManager cam_%d: pytapo probe exception: %s", camera_id, exc)

        if not ok:
            if preferred == "tapo":
                # User explicitly chose Tapo — treat probe failure as a hard error.
                raise RuntimeError(
                    f"Camera {camera_id}: preferred_provider=tapo but pytapo probe failed. "
                    "Check IP and camera-account credentials."
                )
            logger.info(
                "StreamManager cam_%d: pytapo probe failed — falling back to OpenCV", camera_id
            )
            return False

        # Probe succeeded — store client and start poller.
        self._tapo_clients[camera_id] = client
        poller = TapoPoller(
            camera_id=camera_id,
            tapo_client=client,
            on_event=self._on_tapo_event,
            on_status_change=self._on_status_change,
        )
        poller.start()
        self._pollers[camera_id] = poller
        logger.info(
            "StreamManager cam_%d: pytapo active (preferred=%s) — OpenCV motion disabled",
            camera_id,
            preferred,
        )
        return True

    async def _persist_provider(self, camera_id: int, provider: str) -> None:
        """Update the camera's provider column in the DB."""
        from app.database import SessionLocal
        from app.models.camera import Camera

        db = SessionLocal()
        try:
            cam = db.query(Camera).filter(Camera.id == camera_id).first()
            if cam:
                cam.provider = provider
                db.commit()
        except Exception as exc:
            logger.error("StreamManager: provider persist error cam_%d: %s", camera_id, exc)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_all(self) -> None:
        self._loop = asyncio.get_running_loop()
        from app.database import SessionLocal
        from app.models.camera import Camera

        db = SessionLocal()
        try:
            cameras = db.query(Camera).all()
            for camera in cameras:
                try:
                    await self.start(camera)
                except Exception as exc:
                    logger.error("StreamManager: start_all error for cam_%d: %s", camera.id, exc)
        finally:
            db.close()

    async def start(self, camera) -> None:
        """
        Orchestrate the per-camera pipeline.  Decides whether to run RTSP and/or
        pytapo based on the camera's auth_method and preferred_provider.
        """
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        camera_id = camera.id
        if camera_id in self._workers or camera_id in self._pollers:
            return

        from app.streaming.mediamtx_client import mediamtx_client
        from app.services.camera_service import get_decrypted_rtsp_url

        needs_rtsp = self.camera_needs_rtsp(camera)
        worker: Optional[RTSPWorker] = None

        if needs_rtsp:
            # Register MediaMTX path + start RTSP worker.
            rtsp_url = get_decrypted_rtsp_url(camera)
            await mediamtx_client.add_path(f"cam_{camera_id}", rtsp_url)

            worker = RTSPWorker(
                camera_id=camera_id,
                on_frame=self._on_frame,
                on_status_change=self._on_status_change,
            )
            self._workers[camera_id] = worker
            worker.start()
            logger.info("StreamManager: started RTSP worker for cam_%d", camera_id)
        else:
            logger.info(
                "StreamManager cam_%d: skipping RTSP (auth_method=cloud_account)",
                camera_id,
            )

        # Try to hand off event detection to pytapo.
        try:
            tapo_ok = await self._try_start_tapo(camera)
        except RuntimeError:
            # preferred_provider="tapo" but probe failed — tear down and re-raise.
            if worker:
                await asyncio.to_thread(worker.stop)
                self._workers.pop(camera_id, None)
                await mediamtx_client.remove_path(f"cam_{camera_id}")
            raise

        # When there is no RTSP worker, pytapo MUST be working — otherwise this
        # camera has no event source at all.  Treat as a hard error.
        if not needs_rtsp and not tapo_ok:
            raise RuntimeError(
                f"Camera {camera_id}: cloud_account auth selected but pytapo probe failed. "
                "Check Tapo email and password."
            )

        if worker is not None:
            worker.motion_detection_enabled = not tapo_ok

        await self._persist_provider(camera_id, "tapo" if tapo_ok else "rtsp")

    async def stop(self, camera_id: int) -> None:
        from app.streaming.mediamtx_client import mediamtx_client

        # Stop poller first.
        poller = self._pollers.pop(camera_id, None)
        if poller:
            await poller.stop()

        self._tapo_clients.pop(camera_id, None)

        worker = self._workers.pop(camera_id, None)
        if worker:
            await asyncio.to_thread(worker.stop)
            await mediamtx_client.remove_path(f"cam_{camera_id}")
            logger.info("StreamManager: stopped worker for cam_%d", camera_id)

    async def stop_all(self) -> None:
        # Stop pollers without workers too — keys are the union of both dicts.
        camera_ids = list(set(self._workers.keys()) | set(self._pollers.keys()))
        for cid in camera_ids:
            await self.stop(cid)

    def active_count(self) -> int:
        return len(self._workers) + len(self._pollers)

    def get_tapo_client(self, camera_id: int):
        """Return the active TapoClient for a camera, or None."""
        return self._tapo_clients.get(camera_id)

    @staticmethod
    def camera_needs_rtsp(camera) -> bool:
        """
        Whether a given camera should run an RTSP worker + MediaMTX path.

        Tapo RTSP only accepts camera-account credentials. When a camera is
        configured with auth_method="cloud_account", the supplied credentials
        will never satisfy RTSP auth — so we skip the RTSP pipeline entirely
        and rely on pytapo for events.  No RTSP also means no live HLS feed
        and no event snapshots for that camera.
        """
        auth_method = getattr(camera, "auth_method", "camera_account")
        preferred = getattr(camera, "preferred_provider", "auto")
        if auth_method == "cloud_account" and preferred in ("auto", "tapo"):
            return False
        return True


stream_manager = StreamManager()
