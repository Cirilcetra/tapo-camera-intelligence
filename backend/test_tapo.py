#!/usr/bin/env python3
"""
Standalone pytapo flow tester.

Usage:
    python test_tapo.py --ip 192.168.1.52 --username admin --password secret

All arguments can also be provided as environment variables:
    TAPO_IP / TAPO_USER / TAPO_PASS

Steps tested:
  1. Probe (auth check)
  2. Basic device info
  3. Motion-detection state
  4. Privacy-mode state
  5. Recent events (last 60 seconds)
  6. Poll events for 10 seconds (live)

No camera is modified — all calls are read-only.
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ts_to_local(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone().strftime("%H:%M:%S")


def ok(msg: str) -> None:
    print(f"  \033[32m✓\033[0m  {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31m✗\033[0m  {msg}")


def info(msg: str) -> None:
    print(f"  \033[34m·\033[0m  {msg}")


def section(title: str) -> None:
    print(f"\n\033[1m── {title}\033[0m")


# ---------------------------------------------------------------------------
# Test steps
# ---------------------------------------------------------------------------

async def step_probe(client) -> bool:
    section("1. Probe (auth check)")
    result = await client.probe()
    if result:
        ok("Authentication successful")
    else:
        fail("Authentication failed — check credentials")
        print()
        print("  Tip: if camera-account auth fails, pytapo will also attempt")
        print("       user=admin with your Tapo cloud account password.")
        print("       Pass --cloud-password <cloud_pass> to enable that fallback.")
    return result


async def step_basic_info(client) -> None:
    section("2. Basic device info")
    try:
        info_data = await client.get_basic_info()
        # Flatten device_info → basic_info if present (KLAP format)
        if "device_info" in info_data and "basic_info" in info_data["device_info"]:
            info_data = info_data["device_info"]["basic_info"]
        fields = [
            ("device_model", "Model"),
            ("sw_version", "Firmware"),
            ("mac", "MAC"),
            ("device_name", "Name"),
            ("device_type", "Type"),
        ]
        for key, label in fields:
            val = info_data.get(key)
            if val:
                ok(f"{label}: {val}")
        if not any(info_data.get(k) for k, _ in fields):
            info(f"Raw response: {info_data}")
    except Exception as exc:
        fail(f"get_basic_info failed: {exc}")


async def step_motion_detection(client) -> None:
    section("3. Motion detection state")
    try:
        md = await client.get_motion_detection()
        enabled = md.get("enabled") == "on"
        sensitivity = md.get("sensitivity") or md.get("digital_sensitivity", "?")
        ok(f"Enabled: {enabled}  |  Sensitivity: {sensitivity}")
    except Exception as exc:
        fail(f"get_motion_detection failed: {exc}")


async def step_privacy_mode(client) -> None:
    section("4. Privacy mode state")
    try:
        pm = await client.get_privacy_mode()
        enabled = pm.get("enabled") == "on"
        ok(f"Privacy mode: {'ON (lens blocked)' if enabled else 'OFF (normal)'}")
    except Exception as exc:
        fail(f"get_privacy_mode failed: {exc}")


async def step_recent_events(client, lookback: int = 60) -> None:
    section(f"5. Recent events (last {lookback}s)")
    start = int(time.time()) - lookback
    end = int(time.time()) + 5
    try:
        events = await client.get_events(start, end)
        if not events:
            info("No events in window")
        for ev in events:
            ok(f"[{ts_to_local(ev['start_ts'])}]  type={ev['type']}")
    except Exception as exc:
        fail(f"get_events failed: {exc}")
        print(f"       {exc}")


async def step_live_poll(client, duration: int = 10, interval: float = 2.0) -> None:
    section(f"6. Live event poll ({duration}s at {interval}s interval)")
    info(f"Watching for new events — trigger motion in front of the camera now...")

    seen: set = set()
    deadline = time.time() + duration

    while time.time() < deadline:
        remaining = deadline - time.time()
        start = int(time.time()) - 5
        end = int(time.time()) + 5
        try:
            events = await client.get_events(start, end)
            for ev in events:
                key = (ev["start_ts"], ev["type"])
                if key not in seen:
                    seen.add(key)
                    ok(f"NEW  [{ts_to_local(ev['start_ts'])}]  type={ev['type']}")
        except Exception as exc:
            fail(f"poll error: {exc}")

        await asyncio.sleep(min(interval, remaining))

    if not seen:
        info("No events detected during live poll")
    else:
        ok(f"Total unique events seen: {len(seen)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> None:
    # Import here so the script works even outside the full venv if pytapo is installed.
    try:
        from app.integrations.tapo_client import TapoClient
    except ImportError:
        # Fallback: import directly from pytapo if running outside the app package
        try:
            from pytapo import Tapo  # noqa: F401
        except ImportError:
            print("ERROR: pytapo is not installed. Run:  pip install pytapo")
            sys.exit(1)

        # Minimal inline shim
        from app.integrations.tapo_client import TapoClient

    print(f"\n\033[1mCamWatcher — pytapo API tester\033[0m")
    print(f"  Camera IP : {args.ip}")
    print(f"  Username  : {args.username}")
    print(f"  Password  : {'*' * len(args.password)}")
    if args.cloud_password:
        print(f"  Cloud PW  : {'*' * len(args.cloud_password)}")

    client = TapoClient(
        host=args.ip,
        username=args.username,
        password=args.password,
        cloud_password=args.cloud_password or "",
    )

    # 1. Must succeed for the rest to make sense
    if not await step_probe(client):
        sys.exit(1)

    await step_basic_info(client)
    await step_motion_detection(client)
    await step_privacy_mode(client)
    await step_recent_events(client, lookback=args.lookback)

    if args.live:
        await step_live_poll(client, duration=args.live_duration, interval=args.poll_interval)

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test pytapo connectivity to a Tapo camera",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ip", default=os.getenv("TAPO_IP"), help="Camera IP address")
    parser.add_argument("--username", default=os.getenv("TAPO_USER", "admin"), help="Camera-account username")
    parser.add_argument("--password", default=os.getenv("TAPO_PASS"), help="Camera-account password")
    parser.add_argument("--cloud-password", default=os.getenv("TAPO_CLOUD_PASS", ""), help="Tapo cloud password (admin fallback)")
    parser.add_argument("--lookback", type=int, default=60, help="Seconds of history to fetch in step 5 (default: 60)")
    parser.add_argument("--live", action="store_true", help="Run the live-poll step")
    parser.add_argument("--live-duration", type=int, default=10, help="Live poll duration in seconds (default: 10)")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Poll interval in seconds (default: 2.0)")

    args = parser.parse_args()

    if not args.ip:
        parser.error("--ip is required (or set TAPO_IP env var)")
    if not args.password:
        parser.error("--password is required (or set TAPO_PASS env var)")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
