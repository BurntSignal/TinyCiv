from __future__ import annotations

import base64
import html
import json
import mimetypes
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush

from engine import TinyCivEngine

HOST = "0.0.0.0"
DIRECT_PORT = int(os.getenv("TINYCIV_DIRECT_PORT", "8787"))
STATIC_DIR = Path(
    os.getenv("TINYCIV_STATIC_DIR", str(Path(__file__).resolve().parent / "static"))
)
DATA_DIR = Path(os.getenv("TINYCIV_DATA_DIR", "/data"))
PUBLIC_URL = os.getenv("TINYCIV_PUBLIC_URL", "https://tinyciv.home.arpa/").rstrip("/") + "/"
VAPID_SUBJECT = os.getenv("TINYCIV_VAPID_SUBJECT", PUBLIC_URL)
PUSH_SUBSCRIPTIONS_PATH = DATA_DIR / "push_subscriptions.json"
VAPID_PRIVATE_KEY_PATH = DATA_DIR / "vapid_private_key.pem"
APP_VERSION = "0.5.8"

engine = TinyCivEngine()
push_lock = threading.RLock()


def json_bytes(data: object) -> bytes:
    return json.dumps(data).encode("utf-8")


def atomic_json_write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(path)


def ensure_vapid_key() -> ec.EllipticCurvePrivateKey:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with push_lock:
        if VAPID_PRIVATE_KEY_PATH.exists():
            key = serialization.load_pem_private_key(
                VAPID_PRIVATE_KEY_PATH.read_bytes(),
                password=None,
            )
            if not isinstance(key, ec.EllipticCurvePrivateKey):
                raise RuntimeError("TinyCiv VAPID key is not an EC private key")
            return key

        key = ec.generate_private_key(ec.SECP256R1())
        VAPID_PRIVATE_KEY_PATH.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        os.chmod(VAPID_PRIVATE_KEY_PATH, 0o600)
        return key


def vapid_public_key() -> str:
    raw = ensure_vapid_key().public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def load_subscriptions() -> list[dict]:
    with push_lock:
        if not PUSH_SUBSCRIPTIONS_PATH.exists():
            return []
        try:
            payload = json.loads(PUSH_SUBSCRIPTIONS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"TinyCiv push: could not read subscriptions ({exc})", flush=True)
            return []
        items = payload.get("subscriptions", []) if isinstance(payload, dict) else []
        return [item for item in items if valid_subscription(item)]


def save_subscriptions(items: list[dict]) -> None:
    with push_lock:
        atomic_json_write(PUSH_SUBSCRIPTIONS_PATH, {"subscriptions": items})


def valid_subscription(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    endpoint = item.get("endpoint")
    keys = item.get("keys")
    return (
        isinstance(endpoint, str)
        and endpoint.startswith("https://")
        and isinstance(keys, dict)
        and isinstance(keys.get("p256dh"), str)
        and isinstance(keys.get("auth"), str)
    )


def add_subscription(subscription: dict) -> int:
    if not valid_subscription(subscription):
        raise ValueError("Invalid Web Push subscription")
    endpoint = subscription["endpoint"]
    with push_lock:
        items = load_subscriptions()
        items = [item for item in items if item.get("endpoint") != endpoint]
        items.append(subscription)
        save_subscriptions(items)
        return len(items)


def remove_subscription(endpoint: str) -> int:
    with push_lock:
        items = load_subscriptions()
        updated = [item for item in items if item.get("endpoint") != endpoint]
        save_subscriptions(updated)
        return len(updated)


def push_payload(title: str, body: str, *, badge: str = "1") -> dict:
    # iOS 18.4+ understands this declarative form directly, while the service
    # worker below also reads the same fields for standards-compatible fallback.
    return {
        "web_push": 8030,
        "notification": {
            "title": title,
            "body": body,
            "navigate": PUBLIC_URL,
            "silent": False,
            "app_badge": badge,
        },
    }


def send_to_subscription(subscription: dict, payload: dict) -> tuple[bool, bool]:
    """Return (delivered, should_remove_subscription)."""
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=str(VAPID_PRIVATE_KEY_PATH),
            vapid_claims={"sub": VAPID_SUBJECT},
            ttl=3600,
        )
        return True, False
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            return False, True
        print(f"TinyCiv push delivery failed: {exc}", flush=True)
        return False, False
    except Exception as exc:
        print(f"TinyCiv push delivery error: {exc}", flush=True)
        return False, False


def send_to_all(payload: dict) -> dict[str, int]:
    ensure_vapid_key()
    with push_lock:
        items = load_subscriptions()

    delivered = 0
    stale_endpoints: set[str] = set()
    for subscription in items:
        ok, stale = send_to_subscription(subscription, payload)
        if ok:
            delivered += 1
        if stale:
            stale_endpoints.add(subscription["endpoint"])

    if stale_endpoints:
        with push_lock:
            current = load_subscriptions()
            save_subscriptions(
                [item for item in current if item.get("endpoint") not in stale_endpoints]
            )

    return {
        "attempted": len(items),
        "delivered": delivered,
        "removed": len(stale_endpoints),
    }


def notification_for_year(year: int) -> dict | None:
    archive = engine.chronicle_export()
    events = [
        event
        for event in archive.get("chronicle", [])
        if int(event.get("year", -1)) == int(year) and bool(event.get("notify"))
    ]
    if not events:
        return None

    first = str(events[0].get("text", "A Chronicle event occurred.")).strip()
    if len(first) > 220:
        first = first[:217].rstrip() + "…"
    if len(events) > 1:
        first += f" (+{len(events) - 1} more Chronicle event{'s' if len(events) != 2 else ''})"

    return push_payload(f"TinyCiv · Year {year}", first)


def simulation_worker() -> None:
    """Advance TinyCiv and deliver queued noteworthy Chronicle events."""
    ensure_vapid_key()

    while True:
        try:
            engine.advance_to_now()
            for year in engine.pending_notification_years():
                payload = notification_for_year(year)
                if payload is not None:
                    result = send_to_all(payload)
                    if result["attempted"]:
                        print(
                            f"TinyCiv push: Year {year} -> "
                            f"{result['delivered']}/{result['attempted']} delivered",
                            flush=True,
                        )
                # Pending years are best-effort notification jobs. Once handled,
                # acknowledge them so a failed endpoint cannot create duplicates.
                engine.acknowledge_notification_year(year)
        except Exception as exc:
            print(f"TinyCiv simulation worker error: {exc}", flush=True)
        time.sleep(60)


class TinyCivHandler(BaseHTTPRequestHandler):
    server_version = "TinyCiv/0.5.8"

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

    def _read_json(self, max_bytes: int = 65536) -> object:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if length < 0 or length > max_bytes:
            raise ValueError("Request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Invalid JSON") from exc

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
            self._send_json({
                "ok": True,
                "version": APP_VERSION,
                "web_push": True,
                "push_subscriptions": len(load_subscriptions()),
            })
            return

        if path == "/api/push/vapid-public-key":
            self._send_json({"public_key": vapid_public_key()})
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

        if path == "/api/push/subscribe":
            try:
                payload = self._read_json()
                if not isinstance(payload, dict):
                    raise ValueError("Subscription must be an object")
                count = add_subscription(payload)
                self._send_json({"ok": True, "subscriptions": count})
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/push/unsubscribe":
            try:
                payload = self._read_json()
                endpoint = payload.get("endpoint") if isinstance(payload, dict) else None
                if not isinstance(endpoint, str) or not endpoint:
                    raise ValueError("Missing subscription endpoint")
                count = remove_subscription(endpoint)
                self._send_json({"ok": True, "subscriptions": count})
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/push/test":
            try:
                payload = self._read_json()
                endpoint = payload.get("endpoint") if isinstance(payload, dict) else None
                if not isinstance(endpoint, str) or not endpoint:
                    raise ValueError("Missing subscription endpoint")

                match = next(
                    (item for item in load_subscriptions() if item.get("endpoint") == endpoint),
                    None,
                )
                if match is None:
                    self._send_json(
                        {"ok": False, "error": "This device is not subscribed"},
                        status=404,
                    )
                    return

                state = engine.public_state()
                test = push_payload(
                    "TinyCiv notifications are alive",
                    f"{state['name']} is currently in Year {state['year']}.",
                )
                delivered, stale = send_to_subscription(match, test)
                if stale:
                    remove_subscription(endpoint)
                if not delivered:
                    self._send_json(
                        {"ok": False, "error": "Push service rejected the test"},
                        status=502,
                    )
                    return
                self._send_json({"ok": True})
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        self._send_json({"error": "not_found"}, status=404)


if __name__ == "__main__":
    ensure_vapid_key()
    threading.Thread(target=simulation_worker, daemon=True).start()
    server = ThreadingHTTPServer((HOST, DIRECT_PORT), TinyCivHandler)
    print(
        f"TinyCiv {APP_VERSION} is alive on port {DIRECT_PORT}. "
        "One real hour = one civilization year. Web Push enabled.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
