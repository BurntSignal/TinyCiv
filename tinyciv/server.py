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
from urllib.parse import parse_qs, urlparse

from engine import TinyCivEngine

HOST = "0.0.0.0"
DIRECT_PORT = int(os.getenv("TINYCIV_DIRECT_PORT", "8787"))
INGRESS_PORT = int(os.getenv("TINYCIV_INGRESS_PORT", "8099"))
INGRESS_ALLOWED_IP = os.getenv("TINYCIV_INGRESS_ALLOWED_IP", "172.30.32.2")
STATIC_DIR = Path(os.getenv("TINYCIV_STATIC_DIR", "/opt/tinyciv/static"))
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")

APP_VERSION = "0.5.5"

engine = TinyCivEngine()


def json_bytes(data: object) -> bytes:
    return json.dumps(data).encode("utf-8")


SETTINGS_PATH = Path(os.getenv("TINYCIV_SETTINGS_PATH", "/data/tinyciv_settings.json"))
SETTINGS_LOCK = threading.RLock()
CHRONICLE_NOTIFICATION_MESSAGE = "A new chronicle entry has occurred!"


def _ha_request(path: str, payload: dict | None = None, method: str = "GET") -> object:
    if not SUPERVISOR_TOKEN:
        raise RuntimeError("SUPERVISOR_TOKEN is unavailable")

    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://supervisor/core{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        raw = response.read()
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def _load_notification_settings() -> dict:
    defaults = {"enabled": True, "notification_entity": ""}
    with SETTINGS_LOCK:
        if not SETTINGS_PATH.exists():
            return defaults.copy()
        try:
            loaded = json.loads(SETTINGS_PATH.read_text())
        except Exception as exc:
            print(f"TinyCiv: notification settings could not be read ({exc}); using defaults.", flush=True)
            return defaults.copy()
        return {
            "enabled": bool(loaded.get("enabled", True)),
            "notification_entity": str(loaded.get("notification_entity", "") or ""),
        }


def _save_notification_settings(settings: dict) -> None:
    normalized = {
        "enabled": bool(settings.get("enabled", True)),
        "notification_entity": str(settings.get("notification_entity", "") or ""),
    }
    with SETTINGS_LOCK:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = SETTINGS_PATH.with_suffix(".tmp")
        temp.write_text(json.dumps(normalized, indent=2))
        temp.replace(SETTINGS_PATH)


def discover_notification_targets() -> list[dict]:
    if not SUPERVISOR_TOKEN:
        return []
    try:
        states = _ha_request("/api/states")
    except Exception as exc:
        print(f"TinyCiv: could not discover Home Assistant notify entities: {exc}", flush=True)
        return []

    targets: list[dict] = []
    if not isinstance(states, list):
        return targets
    for item in states:
        if not isinstance(item, dict):
            continue
        entity_id = str(item.get("entity_id", ""))
        if not entity_id.startswith("notify."):
            continue
        attributes = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
        friendly_name = str(attributes.get("friendly_name") or entity_id)
        targets.append(
            {
                "entity_id": entity_id,
                "name": friendly_name,
                "available": str(item.get("state", "")).lower() != "unavailable",
            }
        )
    targets.sort(key=lambda target: (target["name"].lower(), target["entity_id"]))
    return targets


def notification_settings_payload() -> dict:
    settings = _load_notification_settings()
    targets = discover_notification_targets()
    target_ids = {target["entity_id"] for target in targets}

    # Home Assistant 2026.5+ exposes Companion App devices as notify entities.
    # If there is only one target, arm it automatically so a single-phone setup
    # needs no configuration at all.
    if settings["enabled"] and not settings["notification_entity"] and len(targets) == 1:
        settings["notification_entity"] = targets[0]["entity_id"]
        _save_notification_settings(settings)
    elif settings["notification_entity"] and settings["notification_entity"] not in target_ids:
        # Keep the saved value visible so the UI can explain that it disappeared.
        pass

    return {
        **settings,
        "targets": targets,
        "supervisor_available": bool(SUPERVISOR_TOKEN),
    }


def _resolved_notification_target() -> str:
    payload = notification_settings_payload()
    if not payload["enabled"]:
        return ""

    configured = str(payload.get("notification_entity", ""))
    target_ids = {target["entity_id"] for target in payload.get("targets", []) if target.get("available", True)}
    if configured and configured in target_ids:
        return configured

    available_targets = [target for target in payload.get("targets", []) if target.get("available", True)]
    if len(available_targets) == 1:
        settings = _load_notification_settings()
        settings["notification_entity"] = available_targets[0]["entity_id"]
        _save_notification_settings(settings)
        return available_targets[0]["entity_id"]
    return ""


def _send_push_notification(year: int, message: str = CHRONICLE_NOTIFICATION_MESSAGE) -> bool:
    target = _resolved_notification_target()
    if not target:
        return False
    try:
        _ha_request(
            "/api/services/notify/send_message",
            {
                "entity_id": target,
                "title": "TinyCiv",
                "message": message,
            },
            method="POST",
        )
        print(f"TinyCiv: sent observer notification for Year {year} to {target}.", flush=True)
        return True
    except Exception as exc:
        print(f"TinyCiv: push notification failed for Year {year}: {exc}", flush=True)
        return False


def _send_persistent_fallback(year: int, message: str = CHRONICLE_NOTIFICATION_MESSAGE) -> bool:
    if not SUPERVISOR_TOKEN:
        return False
    try:
        _ha_request(
            "/api/services/persistent_notification/create",
            {
                "title": "TinyCiv",
                "message": message,
                "notification_id": f"tinyciv_chronicle_{year}",
            },
            method="POST",
        )
        print(f"TinyCiv: stored fallback Home Assistant notification for Year {year}.", flush=True)
        return True
    except Exception as exc:
        print(f"TinyCiv: Home Assistant fallback notification failed for Year {year}: {exc}", flush=True)
        return False


def send_chronicle_notification(year: int) -> bool:
    settings = _load_notification_settings()
    if not settings["enabled"]:
        return True
    if _send_push_notification(year):
        return True
    return _send_persistent_fallback(year)


def simulation_worker() -> None:
    while True:
        try:
            engine.advance_to_now()
            for year in engine.pending_notification_years():
                if send_chronicle_notification(year):
                    engine.acknowledge_notification_year(year)
                else:
                    # Keep the year queued and retry later if Home Assistant is temporarily unavailable.
                    break
        except Exception as exc:
            print(f"TinyCiv simulation worker error: {exc}", flush=True)
        time.sleep(60)


class TinyCivHandler(BaseHTTPRequestHandler):
    server_version = "TinyCiv/0.5.5"

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
        ingress_path = self.headers.get("X-Ingress-Path", "").strip()
        if ingress_path:
            base = ingress_path if ingress_path.endswith("/") else ingress_path + "/"
        else:
            base = "/"
        body = (
            template
            .replace("__TINYCIV_BASE__", html.escape(base, quote=True))
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
        if path == "/api/notifications":
            self._send_json(notification_settings_payload())
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
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""

        if path == "/api/nuke":
            self._send_json({"ok": True, "state": engine.nuke()})
            return

        if path == "/api/notifications":
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                self._send_json({"error": "invalid_json"}, status=400)
                return
            current = _load_notification_settings()
            current["enabled"] = bool(payload.get("enabled", current["enabled"]))
            entity_id = str(payload.get("notification_entity", current["notification_entity"]) or "")
            valid_ids = {target["entity_id"] for target in discover_notification_targets()}
            if entity_id and entity_id not in valid_ids:
                self._send_json({"error": "unknown_notification_entity"}, status=400)
                return
            current["notification_entity"] = entity_id
            _save_notification_settings(current)
            self._send_json({"ok": True, **notification_settings_payload()})
            return

        if path == "/api/notifications/test":
            settings = _load_notification_settings()
            if not settings["enabled"]:
                self._send_json({"error": "notifications_disabled"}, status=409)
                return
            if _send_push_notification(0, "TinyCiv observer notifications are connected."):
                self._send_json({"ok": True})
                return
            self._send_json({"error": "notification_target_unavailable"}, status=409)
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
        f"TinyCiv {APP_VERSION} is alive on port {DIRECT_PORT}. One real hour = one civilization year.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
