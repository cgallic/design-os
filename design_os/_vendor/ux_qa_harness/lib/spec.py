"""Load + validate uxqa spec YAML.

Schema (per entry):
  id:               stable slug, lowercase + dashes
  route:            relative to base URL, or absolute URL
  title:            optional human label
  ready_selector:   optional selector that proves this route loaded
  duration_target:  seconds (used by record.py video mode)
  actions:          ordered list of action dicts (see ACTION_TYPES)
                    each action may carry highlight: true to draw cursor halo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ACTION_TYPES = {"goto", "click", "hover", "type", "wait", "scroll", "press"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


@dataclass
class Action:
    type: str
    selector: str | None = None
    text: str | None = None
    url: str | None = None
    delay_ms: int | None = None
    key: str | None = None
    highlight: bool = False
    note: str | None = None


@dataclass
class Entry:
    id: str
    route: str
    narration: str = ""
    duration_target: float = 8.0
    marketing_use: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    title: str | None = None
    panel_selector: str | None = None
    ready_selector: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationIssue:
    entry_id: str
    severity: str
    message: str


def _coerce_action(raw: dict[str, Any]) -> Action:
    t = raw.get("type")
    if t not in ACTION_TYPES:
        raise ValueError(f"invalid action type {t!r} (allowed: {sorted(ACTION_TYPES)})")
    return Action(
        type=t,
        selector=raw.get("selector"),
        text=raw.get("text"),
        url=raw.get("url"),
        delay_ms=raw.get("delay_ms"),
        key=raw.get("key"),
        highlight=bool(raw.get("highlight", False)),
        note=raw.get("note"),
    )


def load(path: Path) -> tuple[list[Entry], list[ValidationIssue]]:
    """Parse + validate spec. Returns (entries, validation_issues).

    Validation runs in two passes:
      1. structural (id format, route shape, action shape) - fail-fast
      2. soft content warnings - collected, returned
    """
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or "entries" not in data:
        raise ValueError("docs-spec.yaml must be a mapping with a top-level `entries` list")

    seen_ids: set[str] = set()
    entries: list[Entry] = []
    issues: list[ValidationIssue] = []

    for raw in data["entries"]:
        if not isinstance(raw, dict):
            raise ValueError(f"entry must be a mapping, got {type(raw).__name__}")
        eid = raw.get("id")
        if not eid or not ID_RE.match(eid):
            raise ValueError(f"invalid id {eid!r}: must match {ID_RE.pattern}")
        if eid in seen_ids:
            raise ValueError(f"duplicate id {eid!r}")
        seen_ids.add(eid)

        route = raw.get("route")
        if not route or not route.startswith("/"):
            raise ValueError(f"{eid}: route must start with `/`")

        narration = raw.get("narration", "").strip()
        marketing = raw.get("marketing_use") or []

        actions_raw = raw.get("actions") or []
        actions = [_coerce_action(a) for a in actions_raw]

        entries.append(
            Entry(
                id=eid,
                route=route,
                narration=narration,
                duration_target=float(raw.get("duration_target", 8)),
                marketing_use=list(marketing),
                actions=actions,
                title=raw.get("title"),
                panel_selector=raw.get("panel_selector"),
                ready_selector=raw.get("ready_selector"),
                raw=raw,
            )
        )
    return entries, issues
