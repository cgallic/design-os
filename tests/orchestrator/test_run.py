from pathlib import Path
from orchestrator.signals import Target
from orchestrator.run import run_target, RunDeps
from critique.runner import CritiqueResult

TARGET = Target(id="kaicalls-homepage", url="https://kaicalls.com", watch_dir=None, vertical="b2c-fintech", brand_pack="bp")


def _critique(score: int, fixes: list[dict]) -> CritiqueResult:
    return CritiqueResult(composite_score=score, issues=[], prioritized_fixes=fixes, pillars={})


def test_run_target_ships_safe_when_score_passes_on_first_pass(tmp_path):
    critiques = [_critique(28, [])]  # high score, no fixes needed
    submitted = {}

    deps = RunDeps(
        render=lambda target: tmp_path / "run1",
        critique=lambda run_dir: critiques.pop(0),
        apply_deterministic_fix=lambda finding, overrides_path: True,
        overrides_dir=tmp_path,
        submit_item=lambda item: submitted.update(item=item) or "item-1",
        finalize_item=lambda item_id: submitted.setdefault("finalized", item_id),
        gate_for=lambda target: "safe",
        run_date="2026-07-02",
        pass_threshold=25,
    )

    result = run_target(TARGET, deps)

    assert result["iterations"] == 1
    assert result["final_score"] == 28
    assert result["gate"] == "safe"
    assert submitted["item"]["gate"] == "safe"
    assert submitted["finalized"] == "item-1"


def test_run_target_applies_deterministic_fixes_and_reruns(tmp_path):
    critiques = [
        _critique(15, [{"priority": "P0", "fix": "Add button styling", "pillar": "visual_cohesion", "heuristic": "Affordance Collapse", "description": "CTA looks like text"}]),
        _critique(27, []),
    ]
    applied = []

    deps = RunDeps(
        render=lambda target: tmp_path / "run1",
        critique=lambda run_dir: critiques.pop(0),
        apply_deterministic_fix=lambda finding, overrides_path: applied.append(finding) or True,
        overrides_dir=tmp_path,
        submit_item=lambda item: "item-2",
        finalize_item=lambda item_id: None,
        gate_for=lambda target: "safe",
        run_date="2026-07-02",
        pass_threshold=25,
    )

    result = run_target(TARGET, deps)

    assert result["iterations"] == 2
    assert result["final_score"] == 27
    assert len(applied) == 1


def test_run_target_stops_at_max_iterations_and_still_ships(tmp_path):
    low_critique = _critique(10, [{"priority": "P0", "fix": "x", "pillar": "visual_cohesion", "heuristic": "Affordance Collapse", "description": "still broken"}])
    critiques = [low_critique, low_critique, low_critique]
    submitted = {}

    deps = RunDeps(
        render=lambda target: tmp_path / "run1",
        critique=lambda run_dir: critiques.pop(0) if critiques else low_critique,
        apply_deterministic_fix=lambda finding, overrides_path: True,
        overrides_dir=tmp_path,
        submit_item=lambda item: submitted.update(item=item) or "item-3",
        finalize_item=lambda item_id: None,
        gate_for=lambda target: "safe",
        run_date="2026-07-02",
        pass_threshold=25,
    )

    result = run_target(TARGET, deps, max_iterations=3)

    assert result["iterations"] == 3
    assert result["gate"] == "safe"
    assert submitted["item"]["risk_tier"] in ("low", "medium")  # iteration-capped items are flagged, per spec section 8


def test_run_target_flags_risk_tier_on_early_exit_while_still_failing(tmp_path):
    # heuristic/description that classify_finding won't recognize -> classified "flag",
    # so no deterministic fix is applied and the loop exits early on iteration 1,
    # well before max_iterations, while still below pass_threshold.
    low_critique = _critique(
        10,
        [{"priority": "P0", "fix": "rethink the tone", "pillar": "visual_cohesion",
          "heuristic": "Tone Mismatch", "description": "copy tone feels off-brand"}],
    )
    submitted = {}

    deps = RunDeps(
        render=lambda target: tmp_path / "run1",
        critique=lambda run_dir: low_critique,
        apply_deterministic_fix=lambda finding, overrides_path: True,
        overrides_dir=tmp_path,
        submit_item=lambda item: submitted.update(item=item) or "item-4",
        finalize_item=lambda item_id: None,
        gate_for=lambda target: "safe",
        run_date="2026-07-02",
        pass_threshold=25,
    )

    result = run_target(TARGET, deps, max_iterations=3)

    assert result["iterations"] == 1
    assert result["iterations"] < 3
    assert submitted["item"]["risk_tier"] == "medium"
