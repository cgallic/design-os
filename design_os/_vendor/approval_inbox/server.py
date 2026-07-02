"""Approval Inbox — minimal stdlib HTTP server.

    GET  /                              → the dashboard (dashboard/index.html)
    GET  /api/items                     → JSON list of all items
    POST /api/items/<id>/approve        → human approves (+ executes if runnable)
    POST /api/items/<id>/dismiss        → terminal reject/skip
    POST /api/items/<id>/agent          → agent attempts execution (gate-checked)

There is NO real execution. The store's default executor is a stub that records
a result without performing side effects. Irreversible items refuse to execute
without an explicit /approve first.

Run:
    python -m approval_inbox.server          # serves on 127.0.0.1:8799
    python -m approval_inbox.server 9000     # custom port
"""
from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DASHBOARD_DIR = ROOT / "dashboard"

sys.path.insert(0, str(ROOT))
from approval_inbox.store import ApprovalStore, StateError  # noqa: E402

# Map the API verb to the store's transition action.
_ACTION_MAP = {"approve": "approve", "dismiss": "dismiss", "agent": "agent_do"}

# One process-wide store. Auto-seeds from fixtures on first boot if empty.
_STORE: ApprovalStore | None = None


def get_store() -> ApprovalStore:
    global _STORE
    if _STORE is None:
        _STORE = ApprovalStore()
        if _STORE.summary()["items"] == 0:
            from approval_inbox.store import _seed_from_fixtures
            _seed_from_fixtures(_STORE)
    return _STORE


class Handler(BaseHTTPRequestHandler):
    server_version = "ApprovalInbox/0.1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._send_file(DASHBOARD_DIR / "index.html")
            return
        if path == "/api/items":
            self._json({"ok": True, "items": get_store().list()})
            return
        # static dashboard assets (none by default, but kept safe)
        target = (DASHBOARD_DIR / path.lstrip("/")).resolve()
        if (DASHBOARD_DIR in target.parents) and target.is_file():
            self._send_file(target)
            return
        self._json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parts = [unquote(p) for p in urlparse(self.path).path.strip("/").split("/")]
        if len(parts) == 4 and parts[:2] == ["api", "items"]:
            item_id, verb = parts[2], parts[3]
            action = _ACTION_MAP.get(verb)
            if action is None:
                self._json({"ok": False, "error": f"unknown action: {verb}"},
                           HTTPStatus.BAD_REQUEST)
                return
            try:
                item = get_store().transition(item_id, action, actor=f"dashboard:{verb}")
            except KeyError as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            except StateError as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.CONFLICT)
                return
            except Exception as exc:  # pragma: no cover - defensive
                self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                           HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json({"ok": True, "item": item, "result": item.get("result")})
            return
        self._json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[approval-inbox] " + fmt % args + "\n")

    # ---- helpers -------------------------------------------------------
    def _send_file(self, path: Path) -> None:
        if not path.exists():
            self._json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    host = "127.0.0.1"
    port = int(argv[0]) if argv else 8799
    get_store()  # boot + auto-seed
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"[approval-inbox] serving http://{host}:{port}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[approval-inbox] stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
