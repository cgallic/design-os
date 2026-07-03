from datetime import date

import pytest

from design_os.lint.engine import Binding, blocking_failures, load_bindings, run_lint
from design_os.rules.loader import Rule, Waiver


def _rule(rule_id="A11Y-001", check_type="deterministic", severity="block", threshold=">= 4.5:1"):
    return Rule(
        id=rule_id,
        statement="Text contrast meets WCAG AA.",
        category="accessibility",
        check_type=check_type,
        threshold=threshold,
        severity=severity,
        rationale="WCAG 1.4.3",
    )


FAILING_SNAPSHOT = {
    "text_styles": [
        {
            "selector": "p.hero",
            "font_size_px": 16.0,
            "font_weight": 400,
            "line_height_px": 24.0,
            "color": "rgb(170, 170, 170)",
            "background_color": "rgb(255, 255, 255)",
            "chars_per_line": 70,
            "is_large_text": False,
            "sample_text": "x" * 200,
        }
    ]
}


def test_bound_rule_runs_and_fails():
    verdicts = run_lint(
        FAILING_SNAPSHOT,
        [_rule()],
        [Binding(rule_id="A11Y-001", check="contrast_min", params={})],
        target_id="kaicalls-homepage",
    )
    assert verdicts[0].status == "fail"
    assert blocking_failures(verdicts) == [verdicts[0]]


def test_unbound_deterministic_rule_reports_unimplemented():
    verdicts = run_lint(FAILING_SNAPSHOT, [_rule()], [], target_id="t")
    assert verdicts[0].status == "unimplemented"


def test_vision_rules_are_not_linted():
    rule = _rule(rule_id="HIER-001", check_type="vision", threshold="one focal point")
    assert run_lint(FAILING_SNAPSHOT, [rule], [], target_id="t") == []


def test_waived_failure_is_visible_not_silent():
    waiver = Waiver(
        rule_id="A11Y-001",
        scope="kaicalls-*",
        rationale="Ghost hero text is decorative during brand refresh sprint.",
        expires=date(2027, 1, 1),
        approved_by="connor",
    )
    verdicts = run_lint(
        FAILING_SNAPSHOT,
        [_rule()],
        [Binding(rule_id="A11Y-001", check="contrast_min", params={})],
        target_id="kaicalls-homepage",
        waivers=[waiver],
    )
    assert verdicts[0].status == "waived"
    assert "brand refresh" in verdicts[0].evidence
    assert blocking_failures(verdicts) == []


def test_load_bindings_rejects_unknown_check(tmp_path):
    path = tmp_path / "bindings.yaml"
    path.write_text("bindings:\n  - rule_id: A11Y-001\n    check: not_a_check\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown check"):
        load_bindings(path)


def test_load_bindings_missing_file_is_empty(tmp_path):
    assert load_bindings(tmp_path / "nope.yaml") == []
