import asyncio
import logging
from typing import Optional

import cv2
from sqlalchemy.orm import Session

from app.models.camera import Camera
from app.services.crypto import decrypt_password, encrypt_password

logger = logging.getLogger(__name__)

# Timeout in seconds for test-connection capture attempt
TEST_TIMEOUT = 8


def build_rtsp_url(ip: str, username: str, password: str, rtsp_path: str) -> str:
    return f"rtsp://{username}:{password}@{ip}/{rtsp_path}"


def create_camera(
    db: Session,
    name: str,
    ip: str,
    username: str,
    password: str,
    rtsp_path: str = "stream1",
    preferred_provider: str = "auto",
    auth_method: str = "camera_account",
) -> Camera:
    rtsp_url = build_rtsp_url(ip, username, password, rtsp_path)
    password_encrypted = encrypt_password(password)
    camera = Camera(
        name=name,
        ip=ip,
        rtsp_url=rtsp_url,
        username=username,
        password_encrypted=password_encrypted,
        rtsp_path=rtsp_path,
        preferred_provider=preferred_provider,
        auth_method=auth_method,
        status="offline",
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


def get_decrypted_rtsp_url(camera: Camera) -> str:
    password = decrypt_password(camera.password_encrypted)
    return build_rtsp_url(camera.ip, camera.username, password, camera.rtsp_path)


async def test_rtsp_connection(ip: str, username: str, password: str, rtsp_path: str) -> bool:
    """
    Try to open an RTSP stream. Returns True if a frame can be grabbed within TEST_TIMEOUT seconds.
    Runs in a thread to avoid blocking the event loop.
    """
    url = build_rtsp_url(ip, username, password, rtsp_path)

    def _try_capture() -> bool:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, TEST_TIMEOUT * 1000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, TEST_TIMEOUT * 1000)
        try:
            if not cap.isOpened():
                return False
            ret, _ = cap.read()
            return ret
        except Exception:
            return False
        finally:
            cap.release()

    return await asyncio.to_thread(_try_capture)
