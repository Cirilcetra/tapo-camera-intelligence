import atexit
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

import uvicorn

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MEDIAMTX_DIR = Path(__file__).parent.parent / "mediamtx"
MEDIAMTX_BIN = MEDIAMTX_DIR / "mediamtx"
MEDIAMTX_CFG = MEDIAMTX_DIR / "mediamtx.yml"
MEDIAMTX_READY_TIMEOUT = 10  # seconds


def start_mediamtx() -> subprocess.Popen | None:
    if not MEDIAMTX_BIN.exists():
        logger.warning("MediaMTX binary not found at %s — skipping", MEDIAMTX_BIN)
        return None

    logger.info("Starting MediaMTX…")
    proc = subprocess.Popen(
        [str(MEDIAMTX_BIN), str(MEDIAMTX_CFG)],
        cwd=str(MEDIAMTX_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Wait until the API port is accepting connections
    import socket
    deadline = time.monotonic() + MEDIAMTX_READY_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            out, _ = proc.communicate()
            logger.error("MediaMTX exited early:\n%s", out)
            return None
        try:
            with socket.create_connection(("127.0.0.1", 9997), timeout=0.5):
                logger.info("MediaMTX ready (API on :9997, HLS on :8888, RTSP on :8554)")
                return proc
        except OSError:
            time.sleep(0.3)

    logger.error("MediaMTX did not become ready within %ds", MEDIAMTX_READY_TIMEOUT)
    proc.terminate()
    return None


def stop_mediamtx(proc: subprocess.Popen) -> None:
    if proc and proc.poll() is None:
        logger.info("Stopping MediaMTX…")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    mtx_proc = start_mediamtx()

    if mtx_proc:
        atexit.register(stop_mediamtx, mtx_proc)

        def _sigterm(sig, frame):
            stop_mediamtx(mtx_proc)
            sys.exit(0)

        signal.signal(signal.SIGTERM, _sigterm)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
