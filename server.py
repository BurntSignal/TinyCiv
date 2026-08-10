\
from __future__ import annotations

import json
import mimetypes
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from engine import TinyCivEngine

HOST = "0.0.0.0"
PORT = 8787
STATIC_DIR = Path("/opt/tinyciv/static")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")

engine = TinyCivEngine()


def json_bytes(data: object) -> bytes:
    return json.dumps(data).encode("utf-8")


def send_ha_notification(event: dict) -> None:
    if not SUPERVISOR_TOKEN:
        print("TinyCiv: no SUPERVISOR_TOKEN; skipping Home Assistant notification.")
        return

    payload = json.dumps(
        {
            "title": f"TinyCiv — Year {event['year']}",
            "message": event["text"],
            "notification_id": "tinyciv_chronicle",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "http://supervisor/core/api/services/persistent_notification/create",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            response.read()
        print(f"TinyCiv: notified HA about Year {event['year']}: {event['text']}")
    except Exception as exc:
        print(f"TinyCiv: Home Assistant notification failed: {exc}")


def simulation_worker() -> None:
    while True:
        try:
            events = engine.advance_to_now()
            notify_events = [e for e in events if e.get("notify")]
            if notify_events:
                # One HA notification per catch-up cycle prevents a restart after a long
                # outage from dumping a stack of ancient notifications.
                send_ha_notification(notify_events[-1])
        except Exception as exc:
            print(f"TinyCiv simulation worker error: {exc}")
        time.sleep(60)


class TinyCivHandler(BaseHTTPRequestHandler):
    server_version = "TinyCiv/0.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"TinyCiv HTTP: {self.address_string()} - {fmt % args}")

    def _send_json(self, data: object, status: int = 200) -> None:
        body = json_bytes(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, relative: str) -> None:
        candidate = (STATIC_DIR / relative).resolve()
        if not str(candidate).startswith(str(STATIC_DIR.resolve())) or not candidate.is_file():
            self.send_error(404)
            return

        body = candidate.read_bytes()
        content_type, _ = mimetypes.guess_type(str(candidate))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/health":
            self._send_json({"ok": True})
            return
        if path == "/api/state":
            self._send_json(engine.public_state())
            return
        if path == "/api/visit":
            self._send_json(engine.visit())
            return

        if path == "/":
            self._serve_file("index.html")
            return

        relative = path.lstrip("/")
        self._serve_file(relative)

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/nuke":
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            new_state = engine.nuke()
            self._send_json({"ok": True, "state": new_state})
            return

        self._send_json({"error": "not_found"}, status=404)


if __name__ == "__main__":
    thread = threading.Thread(target=simulation_worker, daemon=True)
    thread.start()

    server = ThreadingHTTPServer((HOST, PORT), TinyCivHandler)
    print(f"TinyCiv is alive on port {PORT}. One real hour = one civilization year.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
