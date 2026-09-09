from __future__ import annotations

import html
import json
import mimetypes
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from engine import TinyCivEngine

HOST = "0.0.0.0"
DIRECT_PORT = int(os.getenv("TINYCIV_DIRECT_PORT", "8787"))
STATIC_DIR = Path(
    os.getenv("TINYCIV_STATIC_DIR", str(Path(__file__).resolve().parent / "static"))
)
APP_VERSION = "0.5.7"

engine = TinyCivEngine()


def json_bytes(data: object) -> bytes:
    return json.dumps(data).encode("utf-8")


def simulation_worker() -> None:
    """Advance TinyCiv and discard legacy notification jobs.

    Pending observer-notification years are acknowledged without delivery so
    the future Web Push implementation starts with only new Chronicle events.
    """
    while True:
        try:
            engine.advance_to_now()
            for year in engine.pending_notification_years():
                engine.acknowledge_notification_year(year)
        except Exception as exc:
            print(f"TinyCiv simulation worker error: {exc}", flush=True)
        time.sleep(60)


class TinyCivHandler(BaseHTTPRequestHandler):
    server_version = "TinyCiv/0.5.7"

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

    def _send_text_download(self, text: str, filename: str) -> None:
        body = text.encode("utf-8")
        safe_filename = "".join(
            char if char.isascii() and (char.isalnum() or char in {"-", "_", "."}) else "-"
            for char in filename
        ).strip("-") or "TinyCiv-Chronicle.txt"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{safe_filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self) -> None:
        template = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        body = (
            template
            .replace("__TINYCIV_BASE__", "/")
            .replace("__TINYCIV_VERSION__", html.escape(APP_VERSION, quote=True))
            .encode("utf-8")
        )
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
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self._send_json({"ok": True, "version": APP_VERSION})
            return

        if path == "/api/chronicle.txt":
            archive = engine.chronicle_export()
            lines = [
                "TinyCiv — The Chronicle",
                f"Civilization: {archive['name']}",
                f"Current Year: {archive['year']}",
                f"Era: {archive['era']}",
                "",
            ]
            entries = archive.get("chronicle", [])
            if entries:
                for event in entries:
                    lines.append(f"YR {event['year']} — {event['text']}")
            else:
                lines.append("The chronicle is waiting for its first entry.")
            lines.append("")
            filename = f"TinyCiv-{archive['name']}-Chronicle-YR{archive['year']}.txt"
            self._send_text_download("\n".join(lines), filename)
            return

        if path == "/api/state":
            try:
                page = int(query.get("chronicle_page", ["1"])[0])
                page_size = int(query.get("page_size", ["12"])[0])
            except ValueError:
                page = 1
                page_size = 12
            order = query.get("chronicle_order", ["desc"])[0]
            self._send_json(engine.public_state(page, order, page_size))
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
            self._send_json({"ok": True, "state": engine.nuke()})
            return

        self._send_json({"error": "not_found"}, status=404)


if __name__ == "__main__":
    threading.Thread(target=simulation_worker, daemon=True).start()
    server = ThreadingHTTPServer((HOST, DIRECT_PORT), TinyCivHandler)
    print(
        f"TinyCiv {APP_VERSION} is alive on port {DIRECT_PORT}. "
        "One real hour = one civilization year.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
