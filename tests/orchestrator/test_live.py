from pathlib import Path

import yaml

from design_os.orchestrator.live import (
    build_audit_spec,
    write_rubric_prompt_file,
    gate_for,
    build_live_deps,
    run_watchlist_live,
)
from design_os.orchestrator.signals import Target
from design_os.orchestrator.run import RunDeps
from design_os.dashboard.build import init_db


def test_build_audit_spec_writes_a_single_homepage_entry(tmp_path):
    spec_path = build_audit_spec(tmp_path)
    data = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    assert "entries" in data
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["id"] == "home"
    assert entry["route"] == "/"


def test_write_rubric_prompt_file_writes_the_composed_rubric(tmp_path):
    prompt_path = write_rubric_prompt_file(tmp_path)
    content = prompt_path.read_text(encoding="utf-8")
    assert "Three Pillars" in content
    assert "<<PATH>>" in content


def test_gate_for_always_returns_safe_since_no_publish_driver_exists():
    target = Target(id="x", url="https://example.com", watch_dir=None, vertical="b2b-saas", brand_pack=None)
    assert gate_for(target) == "safe"


def test_build_live_deps_returns_a_fully_wired_rundeps(tmp_path):
    from design_os._vendor.approval_inbox import ApprovalStore

    store = ApprovalStore(db_path=tmp_path / "inbox.db", jsonl_path=tmp_path / "inbox.jsonl")
    deps = build_live_deps(work_root=tmp_path, store=store, run_date="2026-07-02")

    assert isinstance(deps, RunDeps)
    assert deps.run_date == "2026-07-02"
    assert deps.overrides_dir == tmp_path / "overrides"
    assert deps.overrides_dir.exists()
    target = Target(id="x", url="https://example.com", watch_dir=None, vertical="b2b-saas", brand_pack=None)
    assert deps.gate_for(target) == "safe"
    # apply_deterministic_fix is a no-op for audit-only live wiring: never raises, never writes.
    assert deps.apply_deterministic_fix({"heuristic": "Affordance Collapse"}, tmp_path / "x.css") is False
    assert not (tmp_path / "x.css").exists()


def test_run_watchlist_live_skips_watch_dir_targets(tmp_path, capsys):
    db_path = tmp_path / "dashboard.db"
    init_db(db_path)
    url_target = Target(id="a", url="https://a.example", watch_dir=None, vertical="b2b-saas", brand_pack=None)
    dir_target = Target(id="b", url=None, watch_dir="/some/dir", vertical="b2b-saas", brand_pack=None)

    calls = []

    def fake_run_target(target, deps, max_iterations):
        calls.append((target.id, max_iterations))
        return {"target_id": target.id, "final_score": 28, "iterations": 1, "gate": "safe", "item_id": "item-1"}

    results = run_watchlist_live(
        [url_target, dir_target], deps=object(), dashboard_db_path=db_path, run_target_fn=fake_run_target
    )

    assert calls == [("a", 1)]  # dir_target skipped, url_target run with max_iterations=1
    assert len(results) == 1
    assert results[0]["target_id"] == "a"
    captured = capsys.readouterr()
    assert "SKIP" in captured.out
    assert "b" in captured.out


def test_run_watchlist_live_records_each_result_to_the_dashboard(tmp_path):
    db_path = tmp_path / "dashboard.db"
    init_db(db_path)
    url_target = Target(id="a", url="https://a.example", watch_dir=None, vertical="b2b-saas", brand_pack=None)

    def fake_run_target(target, deps, max_iterations):
        return {"target_id": target.id, "final_score": 28, "iterations": 1, "gate": "safe", "item_id": "item-1"}

    run_watchlist_live([url_target], deps=object(), dashboard_db_path=db_path, run_target_fn=fake_run_target)

    import sqlite3

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT target_id, final_score FROM runs").fetchone()
    assert row == ("a", 28)
