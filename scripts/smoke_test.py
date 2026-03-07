#!/usr/bin/env python3
"""Minimal end-to-end smoke test for analysis + monitoring flows.

Usage:
  python scripts/smoke_test.py

Assumes backend (8000) and frontend (5173) are already running.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass

import httpx
import websockets

FRONTEND_BASE = "http://127.0.0.1:5173"
WS_BASE = "ws://127.0.0.1:5173/ws/audio/monitoring"


@dataclass
class SmokeSummary:
    analysis_ok: bool
    analysis_status: str
    monitor_ok: bool
    monitor_last_type: str


def run_analysis_flow() -> tuple[bool, str]:
    print("=== Analysis Flow ===")
    with httpx.Client(timeout=30.0) as client:
        page = client.get(f"{FRONTEND_BASE}/analysis")
        print("analysis_page_status=", page.status_code)
        if page.status_code != 200:
            return False, "page_unreachable"

        files = {
            "file": (
                "smoke_case.txt",
                "我是公安局的，请你立即转账到安全账户。".encode("utf-8"),
                "text/plain",
            )
        }
        upload = client.post(f"{FRONTEND_BASE}/api/analysis/upload", files=files)
        print("upload_status=", upload.status_code)
        if upload.status_code != 200:
            return False, "upload_failed"

        upload_payload = upload.json()
        analysis_id = upload_payload.get("analysis_id")
        print("analysis_id=", analysis_id)
        if not analysis_id:
            return False, "analysis_id_missing"

        final_status = "processing"
        for i in range(30):
            time.sleep(0.3)
            poll = client.get(f"{FRONTEND_BASE}/api/analysis/results/{analysis_id}")
            if poll.status_code != 200:
                print(f"poll[{i}] status={poll.status_code}")
                return False, "poll_failed"

            payload = poll.json()
            final_status = str(payload.get("status", "unknown"))
            print(f"poll[{i}] -> {final_status}")

            if final_status in {"completed", "failed"}:
                break

        if final_status != "completed":
            return False, final_status

    return True, final_status


async def run_monitor_flow() -> tuple[bool, str]:
    print("=== Monitor Flow ===")

    try:
        with httpx.Client(timeout=30.0) as client:
            session_response = client.post(
                f"{FRONTEND_BASE}/api/monitoring/session",
                json={
                    "sensitivity_level": "medium",
                    "alert_types": ["voice_biometrics", "behavioral", "content"],
                    "auto_record": True,
                },
            )
            print("monitor_session_status=", session_response.status_code)
            if session_response.status_code != 200:
                return False, "session_create_failed"

            session_payload = session_response.json()
            session_id = str(session_payload.get("session_id") or "")
            print("monitor_session_id=", session_id)
            if not session_id:
                return False, "session_id_missing"

        ws_url = f"{WS_BASE}?session_id={session_id}"
        async with websockets.connect(ws_url, max_size=2**20) as ws:
            first = json.loads(await ws.recv())
            first_type = str(first.get("type", ""))
            print("first_event=", first_type)
            if first_type != "connection_established":
                return False, first_type or "unexpected_first_event"

            last_type = first_type
            for i in range(25):
                await ws.send(b"\x00" * 4096)
                payload = json.loads(await ws.recv())
                last_type = str(payload.get("type", ""))
                print(f"monitor_event[{i}]={last_type}")

                # In strict mode, this may become error quickly if dependencies are missing.
                if last_type in {"error", "fraud_alert"}:
                    break

            # Monitor flow is considered wired if we receive at least one backend event after connect.
            ok = last_type in {"risk_analysis", "fraud_alert", "error"}
            return ok, last_type or "no_event"

    except Exception as exc:  # pragma: no cover
        print("monitor_exception=", exc)
        return False, "exception"


def main() -> int:
    analysis_ok, analysis_status = run_analysis_flow()
    monitor_ok, monitor_last_type = asyncio.run(run_monitor_flow())

    summary = SmokeSummary(
        analysis_ok=analysis_ok,
        analysis_status=analysis_status,
        monitor_ok=monitor_ok,
        monitor_last_type=monitor_last_type,
    )

    print("=== Summary ===")
    print(summary)

    if analysis_ok and monitor_ok:
        print("SMOKE_TEST=PASS")
        return 0

    print("SMOKE_TEST=FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
