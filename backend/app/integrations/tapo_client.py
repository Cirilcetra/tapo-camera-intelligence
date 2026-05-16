"""
Async wrapper around the synchronous pytapo.Tapo client.

All pytapo calls are blocking (uses `requests` internally), so every method
dispatches via `asyncio.to_thread` to keep the FastAPI event loop free.

Authentication notes (from pytapo docs):
  - First try with the camera-account credentials (username + password set in
    the Tapo app under Settings → Advanced Settings → Camera Account).
  - If that raises an auth exception, fall back to user="admin" + the user's
    Tapo cloud account password passed as `cloud_password`.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Maps numeric alarm_type codes from searchDetectionList to human-readable names.
# Based on community research of the Tapo API.
ALARM_TYPE_MAP: dict[str, str] = {
    "0": "motion",
    "1": "person",
    "2": "vehicle",
    "3": "pet",
    "4": "baby",
    "5": "package",
    "6": "bark",
    "7": "meow",
    "8": "glass_break",
    "9": "tamper",
}


def _alarm_type_to_label(alarm_type) -> str:
    """Convert a raw alarm_type value (int or str) to a label string."""
    return ALARM_TYPE_MAP.get(str(alarm_type), f"event_{alarm_type}")


class TapoClient:
    """
    Async facade over pytapo.Tapo.

    Instantiate once per camera; call `probe()` before using other methods
    to verify connectivity and authenticate.

    Parameters
    ----------
    auth_method:
      "camera_account" - username/password are the camera-account creds set in
                         the Tapo app under Advanced Settings → Camera Account.
                         Tries those first; falls back to admin + cloud_password
                         if also provided.
      "cloud_account"  - username is the Tapo app email, password is the Tapo
                         app password.  pytapo is invoked as admin + that
                         password (TP-Link's documented cloud-fallback path).
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        cloud_password: str = "",
        auth_method: str = "camera_account",
    ):
        self.host = host
        self.username = username
        self.password = password
        self.cloud_password = cloud_password
        self.auth_method = auth_method
        self._tapo = None  # lazily created in probe()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_tapo(self, user: str, password: str):
        """Build a pytapo.Tapo instance (blocking — call from thread)."""
        from pytapo import Tapo  # imported here to keep module load fast

        return Tapo(
            self.host,
            user,
            password,
            cloudPassword=self.cloud_password,
            printDebugInformation=False,
            printWarnInformation=False,
        )

    def _probe_sync(self) -> bool:
        """
        Try to connect and authenticate per the chosen `auth_method`.

        Returns True on success, False on failure.
        """
        if self.auth_method == "cloud_account":
            # Tapo app login: pytapo wants `admin` as user + the cloud password.
            try:
                tapo = self._build_tapo("admin", self.password)
                tapo.getBasicInfo()
                self._tapo = tapo
                logger.info("TapoClient [%s]: auth OK (cloud_account)", self.host)
                return True
            except Exception as exc:
                logger.warning("TapoClient [%s]: cloud_account auth failed: %s", self.host, exc)
                return False

        # auth_method == "camera_account" (default)
        # Attempt 1: the supplied camera-account credentials.
        try:
            tapo = self._build_tapo(self.username, self.password)
            tapo.getBasicInfo()
            self._tapo = tapo
            logger.info("TapoClient [%s]: auth OK (camera_account)", self.host)
            return True
        except Exception as exc:
            logger.debug("TapoClient [%s]: camera-account auth failed: %s", self.host, exc)

        # Attempt 2: admin + cloud_password fallback if a cloud password was supplied.
        if self.cloud_password:
            try:
                tapo = self._build_tapo("admin", self.cloud_password)
                tapo.getBasicInfo()
                self._tapo = tapo
                logger.info("TapoClient [%s]: auth OK (admin + cloud_password fallback)", self.host)
                return True
            except Exception as exc:
                logger.debug(
                    "TapoClient [%s]: admin+cloud_password auth failed: %s", self.host, exc
                )

        logger.warning("TapoClient [%s]: all auth attempts failed", self.host)
        return False

    def _require_tapo(self):
        if self._tapo is None:
            raise RuntimeError(
                f"TapoClient for {self.host} is not authenticated. Call probe() first."
            )
        return self._tapo

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def probe(self) -> bool:
        """Validate connectivity and authenticate. Returns True on success."""
        return await asyncio.to_thread(self._probe_sync)

    async def get_basic_info(self) -> dict:
        """Return the camera's basic device info dict."""
        tapo = self._require_tapo()
        return await asyncio.to_thread(tapo.getBasicInfo)

    async def get_events(self, start_ts: int, end_ts: int) -> list[dict]:
        """
        Fetch detection events in [start_ts, end_ts] (Unix timestamps).
        Returns a list of normalised dicts: {start_ts, end_ts, type}.
        """
        tapo = self._require_tapo()

        def _fetch():
            return tapo.getEvents(startTime=start_ts, endTime=end_ts)

        raw_events = await asyncio.to_thread(_fetch)
        result = []
        for ev in raw_events:
            alarm_type = ev.get("alarm_type", ev.get("event_type", "0"))
            result.append(
                {
                    "start_ts": int(ev["start_time"]),
                    "end_ts": int(ev["end_time"]),
                    "type": _alarm_type_to_label(alarm_type),
                }
            )
        return result

    async def get_motion_detection(self) -> dict:
        tapo = self._require_tapo()
        return await asyncio.to_thread(tapo.getMotionDetection)

    async def set_motion_detection(self, enabled: bool) -> None:
        tapo = self._require_tapo()
        await asyncio.to_thread(tapo.setMotionDetection, enabled)

    async def get_privacy_mode(self) -> dict:
        tapo = self._require_tapo()
        return await asyncio.to_thread(tapo.getPrivacyMode)

    async def set_privacy_mode(self, enabled: bool) -> None:
        tapo = self._require_tapo()
        await asyncio.to_thread(tapo.setPrivacyMode, enabled)

    async def set_led(self, enabled: bool) -> None:
        tapo = self._require_tapo()
        await asyncio.to_thread(tapo.setLEDEnabled, enabled)

    async def get_controls(self) -> dict:
        """
        Fetch motion-detection, privacy-mode, and LED state in one logical
        call (three separate HTTP requests under the hood).
        """
        tapo = self._require_tapo()

        def _fetch_all():
            result: dict = {}
            try:
                md = tapo.getMotionDetection()
                result["motion_detection"] = {
                    "enabled": md.get("enabled") == "on",
                    "sensitivity": md.get("sensitivity", md.get("digital_sensitivity")),
                }
            except Exception as exc:
                logger.debug("get_controls: motion_detection failed: %s", exc)
                result["motion_detection"] = None

            try:
                pm = tapo.getPrivacyMode()
                result["privacy_mode"] = {"enabled": pm.get("enabled") == "on"}
            except Exception as exc:
                logger.debug("get_controls: privacy_mode failed: %s", exc)
                result["privacy_mode"] = None

            return result

        return await asyncio.to_thread(_fetch_all)
