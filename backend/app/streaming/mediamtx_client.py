import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class MediaMTXClient:
    """Thin async client for the MediaMTX control API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def add_path_sync(self, name: str, source_rtsp_url: str) -> bool:
        """
        Synchronous variant — safe to call from a worker thread.
        Re-registers the path in MediaMTX; idempotent.
        """
        url = f"{self.base_url}/v3/config/paths/add/{name}"
        payload = {"source": source_rtsp_url, "sourceOnDemand": False}
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.post(url, json=payload)
                if resp.status_code in (200, 201):
                    logger.info("MediaMTX (sync): added path %s", name)
                    return True
                body = resp.text
                if "already exists" in body.lower():
                    return True
                logger.warning("MediaMTX (sync) add_path %s: %s %s", name, resp.status_code, body)
                return False
        except Exception as exc:
            logger.warning("MediaMTX (sync) add_path error for %s: %s", name, exc)
            return False

    async def add_path(self, name: str, source_rtsp_url: str) -> bool:
        """Register a new path. Idempotent — ignores 'already exists' errors."""
        url = f"{self.base_url}/v3/config/paths/add/{name}"
        payload = {
            "source": source_rtsp_url,
            "sourceOnDemand": False,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code in (200, 201):
                    logger.info("MediaMTX: added path %s", name)
                    return True
                # 400 with "already exists" is fine on restart
                body = resp.text
                if "already exists" in body.lower():
                    logger.info("MediaMTX: path %s already exists — skipping", name)
                    return True
                logger.warning("MediaMTX add_path %s failed: %s %s", name, resp.status_code, body)
                return False
            except Exception as exc:
                logger.error("MediaMTX add_path error for %s: %s", name, exc)
                return False

    async def remove_path(self, name: str) -> bool:
        """Remove a path. Idempotent — ignores 'not found' errors."""
        url = f"{self.base_url}/v3/config/paths/delete/{name}"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.delete(url)
                if resp.status_code in (200, 204):
                    logger.info("MediaMTX: removed path %s", name)
                    return True
                body = resp.text
                if "not found" in body.lower():
                    logger.info("MediaMTX: path %s not found — nothing to remove", name)
                    return True
                logger.warning("MediaMTX remove_path %s failed: %s %s", name, resp.status_code, body)
                return False
            except Exception as exc:
                logger.error("MediaMTX remove_path error for %s: %s", name, exc)
                return False


mediamtx_client = MediaMTXClient(settings.MEDIAMTX_API_URL)
