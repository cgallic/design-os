"""The harness iron rule at the run_target level: an unwaived 'block' verdict never auto-ships."""
from design_os.critique.runner import CritiqueResult
from design_os.gate import build_approval_item
from design_os.lint.engine import Verdict
from design_os.orchestrator.run import RunDeps, run_target
from design_os.orchestrator.signals import Target

TARGET = Target(id="kaicalls-homepage", url="https://kaicalls.com", watch_dir=None, vertical="b2c-fintech", brand_pack="bp")


def _deps(tmp_path, critique, submitted):
    return RunDeps(
        render=lambda target: tmp_path / "run1",
        critique=lambda run_dir: critique,
        apply_deterministic_fix=lambda finding, overrides_path: False,
        overrides_dir=tmp_path,
        submit_item=lambda item: submitted.update(item=item) or "item-1",
        finalize_item=lambda item_id: submitted.setdefault("finalized", item_id),
        gate_for=lambda target: "safe",
        run_date="2026-07-03",
        pass_threshold=25,
    )


def test_blocking_verdict_forces_hold_even_with_high_score(tmp_path):
    critique = CritiqueResult(
        composite_score=29,
        issues=[],
        prioritized_fixes=[],
        pillars={},
        verdicts=[Verdict("A11Y-001", "fail", "nav links 2.1:1 on white", "block")],
    )
    submitted = {}
    result = run_target(TARGET, _deps(tmp_path, critique, submitted), max_iterations=1)
    assert result["gate"] == "irreversible"
    assert "HELD" in submitted["item"]["summary"]
    assert "A11Y-001" in submitted["item"]["summary"]


def test_waived_and_flag_verdicts_do_not_hold(tmp_path):
    critique = CritiqueResult(
        composite_score=29,
        issues=[],
        prioritized_fixes=[],
        pillars={},
        verdicts=[
            Verdict("A11Y-001", "waived", "failed but waived: deliberate ghost text", "block"),
            Verdict("TYPE-002", "fail", "3 typefaces", "flag"),
        ],
    )
    submitted = {}
    result = run_target(TARGET, _deps(tmp_path, critique, submitted), max_iterations=1)
    assert result["gate"] == "safe"
    assert submitted["finalized"] == "item-1"


def test_approval_item_carries_harness_evidence():
    critique = CritiqueResult(
        composite_score=20,
        issues=[],
        prioritized_fixes=[],
        pillars={},
        verdicts=[
            Verdict("A11Y-001", "fail", "nav links 2.1:1", "block"),
            Verdict("TYPE-001", "pass", "body 16px", "flag"),
            Verdict("HIER-001", "waived", "failed but waived: campaign takeover", "block"),
        ],
    )
    item = build_approval_item("kaicalls-homepage", critique, gate="irreversible", dry_run_preview="p", run_date="2026-07-03")
    labels = {e["label"]: e["value"] for e in item["evidence"]}
    assert "harness_verdicts" in labels and "3 rules checked" in labels["harness_verdicts"]
    assert "A11Y-001" in labels["blocking_failures"]
    assert "HIER-001" in labels["waived_rules"]
