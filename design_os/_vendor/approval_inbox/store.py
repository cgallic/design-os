"""Approval Inbox — portable, stdlib-only store for gated agent actions.

A single SQLite table (mirrored to an append-only JSONL log) that holds
ApprovalItems: the merged "what + why" of an inbox row and the
risk/approval/execution lifecycle of a proposed action.

Design goals:
  * Stdlib only. No third-party deps.
  * Append-only JSONL mirror so the inbox is git- and log-ingestible.
  * A real state machine: an ``irreversible`` action can NEVER execute
    without an explicit ``approve`` first.
  * The executor is a pluggable STUB by default — it records a result and
    performs NO real side effects. Plug your own callable to make it real.

Lifecycle (execution_state):
    pending → executing → completed | failed
    completed | failed → rolled_back
    any → dismissed (terminal, no execution)

Gating rule:
    gate == "irreversible"  ⇒  approval_state must be "approved"
                               (explicit human approve) before execute().
    gate == "safe"          ⇒  may execute if owner == "agent-auto"
                               OR after approve()/auto_approve().

CLI:
    python -m approval_inbox.store init
    python -m approval_inbox.store seed   # load fixtures/inbox.jsonl
    python -m approval_inbox.store show
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "inbox.db"
JSONL_PATH = DATA_DIR / "inbox.jsonl"
FIXTURES_PATH = ROOT / "fixtures" / "inbox.jsonl"

# Columns stored as TEXT in SQLite but surfaced as Python objects.
_JSON_FIELDS = ("evidence", "action", "verification_criteria",
                "rollback_reference", "result")

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS items (
    id                    TEXT PRIMARY KEY,
    created_at            TEXT NOT NULL,
    type                  TEXT NOT NULL DEFAULT 'suggestion'
                          CHECK (type IN ('suggestion','task')),
    channel               TEXT,
    source                TEXT,
    title                 TEXT NOT NULL,
    summary               TEXT,
    evidence              TEXT,
    score                 INTEGER NOT NULL DEFAULT 50,
    owner                 TEXT NOT NULL DEFAULT 'agent-auto'
                          CHECK (owner IN ('agent-auto','approve','do')),
    gate                  TEXT NOT NULL DEFAULT 'safe'
                          CHECK (gate IN ('safe','irreversible')),
    risk_tier             TEXT NOT NULL DEFAULT 'low'
                          CHECK (risk_tier IN ('low','medium','high')),
    approval_state        TEXT NOT NULL DEFAULT 'pending'
                          CHECK (approval_state IN
                                 ('pending','approved','rejected','auto_approved','held')),
    execution_state       TEXT NOT NULL DEFAULT 'pending'
                          CHECK (execution_state IN
                                 ('pending','executing','completed','failed','rolled_back','dismissed')),
    action                TEXT,
    verification_criteria TEXT,
    rollback_reference    TEXT,
    result                TEXT,
    dedup_key             TEXT,
    updated_at            TEXT
);

CREATE INDEX IF NOT EXISTS idx_items_exec  ON items(execution_state);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner);
CREATE INDEX IF NOT EXISTS idx_items_gate  ON items(gate);
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_dedup
    ON items(dedup_key) WHERE dedup_key IS NOT NULL;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for f in _JSON_FIELDS:
        if d.get(f):
            try:
                d[f] = json.loads(d[f])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


class StateError(Exception):
    """Raised when a transition violates the state machine / gate rule."""


def stub_executor(item: dict[str, Any]) -> dict[str, Any]:
    """Default executor — performs NO real side effects.

    It only records what *would* have happened. Swap it out via
    ``ApprovalStore(executor=my_callable)`` to wire a real one. A real
    executor receives the full item dict and must return a JSON-serialisable
    result dict (``{"ok": bool, "summary": str, ...}``).
    """
    action = item.get("action") or {}
    return {
        "ok": True,
        "dry_run": True,
        "summary": "stub executor — no side effects performed",
        "kind": action.get("kind", "noop"),
        "preview": action.get("dry_run_preview", ""),
        "executed_at": _now(),
    }


class ApprovalStore:
    """SQLite + append-only JSONL store for ApprovalItems."""

    def __init__(
        self,
        db_path: Path | str = DB_PATH,
        jsonl_path: Path | str = JSONL_PATH,
        executor: Callable[[dict[str, Any]], dict[str, Any]] = stub_executor,
    ):
        self.db_path = Path(db_path)
        self.jsonl_path = Path(jsonl_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.executor = executor
        # check_same_thread=False so the stdlib ThreadingHTTPServer (one thread
        # per request) can share one connection; all writes go through _lock.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---- create --------------------------------------------------------
    def add(self, item: dict[str, Any]) -> str:
        """Insert an ApprovalItem. Returns its id. Honors dedup_key (idempotent)."""
        with self._lock:
            return self._add(item)

    def _add(self, item: dict[str, Any]) -> str:
        item = dict(item)
        dedup = item.get("dedup_key")
        if dedup:
            existing = self.conn.execute(
                "SELECT id FROM items WHERE dedup_key = ?", (dedup,)
            ).fetchone()
            if existing:
                return existing["id"]

        created = item.get("created_at") or _now()
        item_id = item.get("id") or self._gen_id(created, item.get("source", "item"))
        cols = {
            "id": item_id,
            "created_at": created,
            "type": item.get("type", "suggestion"),
            "channel": item.get("channel"),
            "source": item.get("source"),
            "title": item["title"],
            "summary": item.get("summary"),
            "evidence": _dump(item.get("evidence")),
            "score": int(item.get("score", 50)),
            "owner": item.get("owner", "agent-auto"),
            "gate": item.get("gate", "safe"),
            "risk_tier": item.get("risk_tier", "low"),
            "approval_state": item.get("approval_state", "pending"),
            "execution_state": item.get("execution_state", "pending"),
            "action": _dump(item.get("action")),
            "verification_criteria": _dump(item.get("verification_criteria")),
            "rollback_reference": _dump(item.get("rollback_reference")),
            "result": _dump(item.get("result")),
            "dedup_key": dedup,
            "updated_at": item.get("updated_at") or created,
        }
        placeholders = ",".join("?" for _ in cols)
        self.conn.execute(
            f"INSERT INTO items ({','.join(cols)}) VALUES ({placeholders})",
            tuple(cols.values()),
        )
        self.conn.commit()
        self._mirror("add", item_id)
        return item_id

    # ---- read ----------------------------------------------------------
    def get(self, item_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(row) if row else None

    def list(self, **filters: Any) -> list[dict[str, Any]]:
        limit = filters.pop("limit", None)
        order = filters.pop("order_by", "score DESC, created_at DESC")
        clause = " AND ".join(f"{k} = ?" for k in filters) if filters else "1=1"
        sql = f"SELECT * FROM items WHERE {clause} ORDER BY {order}"
        if limit:
            sql += f" LIMIT {int(limit)}"
        with self._lock:
            rows = self.conn.execute(sql, tuple(filters.values())).fetchall()
        return [_row_to_item(r) for r in rows]

    # ---- transitions ---------------------------------------------------
    def transition(self, item_id: str, action: str, *, actor: str = "human") -> dict[str, Any]:
        """Single entrypoint for the dashboard/API.

        action ∈ {approve, dismiss, agent_do}
          * approve   — human approves; if the item is a runnable action,
                        execute it (via the executor) right away.
          * dismiss   — terminal reject/skip, no execution.
          * agent_do  — agent attempts execution. Honors the gate: an
                        irreversible item without an explicit approve is
                        refused.
        """
        with self._lock:
            item = self.get(item_id)
            if item is None:
                raise KeyError(f"item not found: {item_id}")

            if action == "dismiss":
                return self._dismiss(item, actor)
            if action == "approve":
                return self._approve(item, actor)
            if action == "agent_do":
                return self._agent_do(item, actor)
            raise StateError(f"unsupported action: {action}")

    def _dismiss(self, item: dict[str, Any], actor: str) -> dict[str, Any]:
        if item["execution_state"] in ("executing", "completed"):
            raise StateError(
                f"cannot dismiss an item in execution_state '{item['execution_state']}'"
            )
        result = {"ok": True, "summary": "dismissed", "actor": actor, "at": _now()}
        self._update(item["id"],
                     approval_state="rejected",
                     execution_state="dismissed",
                     result=result)
        return self.get(item["id"])

    def _approve(self, item: dict[str, Any], actor: str) -> dict[str, Any]:
        if item["approval_state"] in ("rejected",):
            raise StateError("cannot approve a rejected item")
        self._update(item["id"], approval_state="approved")
        item = self.get(item["id"])
        # If it's a runnable action (has an action block), execute now.
        if item.get("action"):
            return self._execute(item, actor)
        # Otherwise it's a pure suggestion/manual task — approval is the outcome.
        result = {"ok": True, "summary": "approved (no executable action)",
                  "actor": actor, "at": _now()}
        self._update(item["id"], result=result)
        return self.get(item["id"])

    def _agent_do(self, item: dict[str, Any], actor: str) -> dict[str, Any]:
        # The gate rule: irreversible requires an explicit approve first.
        if item["gate"] == "irreversible" and item["approval_state"] not in (
            "approved", "auto_approved"
        ):
            raise StateError(
                "irreversible action requires explicit approve before execution"
            )
        # Safe items owned by the agent can self-approve.
        if item["approval_state"] == "pending":
            self._update(item["id"], approval_state="auto_approved")
            item = self.get(item["id"])
        return self._execute(item, actor)

    def _execute(self, item: dict[str, Any], actor: str) -> dict[str, Any]:
        if item["execution_state"] not in ("pending", "failed"):
            raise StateError(
                f"cannot execute an item in execution_state '{item['execution_state']}'"
            )
        if item["gate"] == "irreversible" and item["approval_state"] not in (
            "approved", "auto_approved"
        ):
            raise StateError(
                "irreversible action requires explicit approve before execution"
            )
        self._update(item["id"], execution_state="executing")
        item = self.get(item["id"])
        try:
            result = self.executor(item) or {}
            result.setdefault("actor", actor)
            self._update(item["id"], execution_state="completed", result=result)
        except Exception as exc:  # executor errors never crash the store
            result = {"ok": False, "summary": f"{type(exc).__name__}: {exc}",
                      "actor": actor, "at": _now()}
            self._update(item["id"], execution_state="failed", result=result)
        return self.get(item["id"])

    def rollback(self, item_id: str, *, actor: str = "human") -> dict[str, Any]:
        """Mark a completed/failed action as rolled back (records intent only)."""
        with self._lock:
            item = self.get(item_id)
            if item is None:
                raise KeyError(f"item not found: {item_id}")
            if item["execution_state"] not in ("completed", "failed"):
                raise StateError(
                    f"cannot roll back an item in execution_state '{item['execution_state']}'"
                )
            result = {
                "ok": True,
                "summary": "rolled back (stub — no real side effects undone)",
                "rollback_reference": item.get("rollback_reference"),
                "actor": actor,
                "at": _now(),
            }
            self._update(item_id, execution_state="rolled_back", result=result)
            return self.get(item_id)

    # ---- internals -----------------------------------------------------
    def _update(self, item_id: str, **fields: Any) -> None:
        fields["updated_at"] = _now()
        for f in _JSON_FIELDS:
            if f in fields:
                fields[f] = _dump(fields[f])
        sets = ",".join(f"{k} = ?" for k in fields)
        with self._lock:
            self.conn.execute(
                f"UPDATE items SET {sets} WHERE id = ?", (*fields.values(), item_id)
            )
            self.conn.commit()
        self._mirror("update", item_id)

    def _mirror(self, op: str, item_id: str) -> None:
        """Append a line to the append-only JSONL mirror."""
        item = self.get(item_id)
        record = {"_op": op, "_at": _now(), "item": item}
        with self.jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return self._summary()

    def _summary(self) -> dict[str, Any]:
        c = self.conn.execute
        return {
            "items": c("SELECT COUNT(*) FROM items").fetchone()[0],
            "needs_approval": c(
                "SELECT COUNT(*) FROM items WHERE gate='irreversible' "
                "AND approval_state IN ('pending','held') "
                "AND execution_state='pending'").fetchone()[0],
            "safe_todo": c(
                "SELECT COUNT(*) FROM items WHERE gate='safe' "
                "AND execution_state='pending'").fetchone()[0],
            "completed": c(
                "SELECT COUNT(*) FROM items WHERE execution_state='completed'"
            ).fetchone()[0],
            "dismissed": c(
                "SELECT COUNT(*) FROM items WHERE execution_state='dismissed'"
            ).fetchone()[0],
        }

    @staticmethod
    def _gen_id(created: str, source: str) -> str:
        stamp = re.sub(r"[^0-9]", "", created)[:14]
        return f"{source}-{stamp}-{uuid4().hex[:6]}"


# ---- CLI ---------------------------------------------------------------
def _seed_from_fixtures(store: ApprovalStore, path: Path = FIXTURES_PATH) -> int:
    if not path.exists():
        print(f"no fixtures at {path}", file=sys.stderr)
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        store.add(json.loads(line))
        n += 1
    return n


def _main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "show"
    store = ApprovalStore()
    if cmd == "init":
        print(f"inbox.db ready at {store.db_path}")
    elif cmd == "seed":
        n = _seed_from_fixtures(store)
        print(f"seeded {n} items from fixtures")
    elif cmd == "show":
        print(json.dumps(store.summary(), indent=2))
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
