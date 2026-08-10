from __future__ import annotations

import html
import json
import mimetypes
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from engine import TinyCivEngine

HOST = "0.0.0.0"
DIRECT_PORT = int(os.getenv("TINYCIV_DIRECT_PORT", "8787"))
INGRESS_PORT = int(os.getenv("TINYCIV_INGRESS_PORT", "8099"))
INGRESS_ALLOWED_IP = os.getenv("TINYCIV_INGRESS_ALLOWED_IP", "172.30.32.2")
STATIC_DIR = Path(os.getenv("TINYCIV_STATIC_DIR", "/opt/tinyciv/static"))
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")

engine = TinyCivEngine()


def json_bytes(data: object) -> bytes:
    return json.dumps(data).encode("utf-8")


def send_ha_notification(event: dict) -> None:
    if not SUPERVISOR_TOKEN:
        print("TinyCiv: no SUPERVISOR_TOKEN; skipping Home Assistant notification.", flush=True)
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
        print(f"TinyCiv: Home Assistant recorded a Year {event['year']} notification.", flush=True)
    except Exception as exc:
        print(f"TinyCiv: Home Assistant notification failed: {exc}", flush=True)


def simulation_worker() -> None:
    while True:
        try:
            events = engine.advance_to_now()
            notify_events = [e for e in events if e.get("notify")]
            if notify_events:
                send_ha_notification(notify_events[-1])
        except Exception as exc:
            print(f"TinyCiv simulation worker error: {exc}", flush=True)
        time.sleep(60)


class TinyCivHandler(BaseHTTPRequestHandler):
    server_version = "TinyCiv/0.2"

    def log_message(self, fmt: str, *args) -> None:
        print(f"TinyCiv HTTP: {self.address_string()} - {fmt % args}", flush=True)

    def _send_json(self, data: object, status: int = 200) -> None:
        body = json_bytes(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self) -> None:
        template = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        ingress_path = self.headers.get("X-Ingress-Path", "").strip()
        if ingress_path:
            base = ingress_path if ingress_path.endswith("/") else ingress_path + "/"
        else:
            base = "/"
        body = template.replace("__TINYCIV_BASE__", html.escape(base, quote=True)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, relative: str) -> None:
        candidate = (STATIC_DIR / relative).resolve()
        static_root = STATIC_DIR.resolve()
        if static_root not in candidate.parents or not candidate.is_file():
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
            self._send_json({"ok": True, "version": "0.2.0"})
            return
        if path == "/api/state":
            self._send_json(engine.public_state())
            return
        if path == "/api/visit":
            self._send_json(engine.visit())
            return
        if path == "/":
            self._serve_index()
            return
        self._serve_file(path.lstrip("/"))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/nuke":
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            self._send_json({"ok": True, "state": engine.nuke()})
            return
        self._send_json({"error": "not_found"}, status=404)


class IngressTinyCivHandler(TinyCivHandler):
    def _allowed(self) -> bool:
        if self.client_address[0] == INGRESS_ALLOWED_IP:
            return True
        self.send_error(403)
        return False

    def do_GET(self) -> None:
        if self._allowed():
            super().do_GET()

    def do_POST(self) -> None:
        if self._allowed():
            super().do_POST()


def run_ingress_server() -> None:
    server = ThreadingHTTPServer((HOST, INGRESS_PORT), IngressTinyCivHandler)
    print(f"TinyCiv ingress is ready on internal port {INGRESS_PORT}.", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    threading.Thread(target=simulation_worker, daemon=True).start()
    threading.Thread(target=run_ingress_server, daemon=True).start()

    server = ThreadingHTTPServer((HOST, DIRECT_PORT), TinyCivHandler)
    print(
        f"TinyCiv 0.2.0 is alive on port {DIRECT_PORT}. One real hour = one civilization year.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
