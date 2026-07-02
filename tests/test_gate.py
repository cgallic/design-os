# tests/test_gate.py
from pathlib import Path
from design_os._vendor.approval_inbox import ApprovalStore
from design_os.critique.runner import CritiqueResult
from design_os.gate import build_approval_item, submit, finalize


def _store(tmp_path):
    return ApprovalStore(db_path=tmp_path / "inbox.db", jsonl_path=tmp_path / "inbox.jsonl")


def _critique():
    return CritiqueResult(
        composite_score=19,
        issues=[{"heuristic": "Affordance Collapse", "description": "CTA looks like text", "severity": 3}],
        prioritized_fixes=[{"priority": "P0", "fix": "Add button styling", "pillar": "visual_cohesion"}],
        pillars={"visual_cohesion": 5},
    )


def test_build_approval_item_shapes_evidence_from_critique():
    item = build_approval_item("kaicalls-homepage", _critique(), gate="safe", dry_run_preview="Would ship draft render.", run_date="2026-07-02")
    assert item["type"] == "task"
    assert item["title"] == "Design review: kaicalls-homepage"
    assert item["gate"] == "safe"
    assert item["owner"] == "agent-auto"
    assert item["action"]["dry_run_preview"] == "Would ship draft render."
    assert any(e["label"] == "composite_score" for e in item["evidence"])


def test_build_approval_item_irreversible_owner_is_approve():
    item = build_approval_item("kaicalls-homepage", _critique(), gate="irreversible", dry_run_preview="Would publish live page.", run_date="2026-07-02")
    assert item["owner"] == "approve"
    assert item["risk_tier"] == "high"


def test_build_approval_item_dedup_key_varies_by_run_date():
    item1 = build_approval_item("kaicalls-homepage", _critique(), gate="safe", dry_run_preview="x", run_date="2026-07-02")
    item2 = build_approval_item("kaicalls-homepage", _critique(), gate="safe", dry_run_preview="x", run_date="2026-07-09")
    assert item1["dedup_key"] != item2["dedup_key"]


def test_submit_and_finalize_safe_item_auto_executes(tmp_path):
    store = _store(tmp_path)
    item = build_approval_item("kaicalls-homepage", _critique(), gate="safe", dry_run_preview="Would ship draft render.", run_date="2026-07-02")
    item_id = submit(store, item)
    finalize(store, item_id)
    stored = store.get(item_id)
    assert stored["execution_state"] == "completed"


def test_submit_and_finalize_irreversible_item_stays_pending(tmp_path):
    store = _store(tmp_path)
    item = build_approval_item("kaicalls-homepage", _critique(), gate="irreversible", dry_run_preview="Would publish live page.", run_date="2026-07-02")
    item_id = submit(store, item)
    finalize(store, item_id)
    stored = store.get(item_id)
    assert stored["approval_state"] == "pending"
    assert stored["execution_state"] == "pending"
