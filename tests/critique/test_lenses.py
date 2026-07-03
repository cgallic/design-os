from datetime import date
from pathlib import Path

import pytest

from design_os.critique.lenses import (
    DEFAULT_LENSES,
    Lens,
    build_lens_prompt,
    merge_lens_verdicts,
    rules_for_lens,
)
from design_os.rules.loader import Rule, Waiver


def _rule(rule_id="HIER-001", category="hierarchy", severity="block"):
    return Rule(
        id=rule_id,
        statement="The page has exactly one dominant focal point above the fold.",
        category=category,
        check_type="vision",
        threshold="exactly 1",
        severity=severity,
        rationale="Hierarchy is the first thing critique checks.",
    )


STRUCTURE = DEFAULT_LENSES[0]


def test_every_vision_category_owned_by_exactly_one_lens():
    owned = [c for lens in DEFAULT_LENSES for c in lens.categories]
    assert len(owned) == len(set(owned)), "a category judged by two lenses is judged carefully by neither"


def test_build_lens_prompt_includes_rules_and_canon(tmp_path):
    canon = tmp_path / "swiss-grid.md"
    canon.write_text("# Canon: Swiss\nThe grid is the skeleton.", encoding="utf-8")
    prompt = build_lens_prompt(STRUCTURE, [_rule()], canon_dir=tmp_path, screenshot_instruction="Open <<PATH>>")
    assert "[HIER-001]" in prompt
    assert "The grid is the skeleton." in prompt
    assert "verdicts" in prompt
    assert "Open <<PATH>>" in prompt


def test_build_lens_prompt_with_no_rules_raises(tmp_path):
    with pytest.raises(ValueError, match="no vision rules"):
        build_lens_prompt(STRUCTURE, [], canon_dir=tmp_path)


def test_rules_for_lens_filters_by_category_and_check_type():
    vision_hier = _rule()
    det_hier = Rule(
        id="HIER-002", statement="s", category="hierarchy", check_type="deterministic",
        threshold="1", severity="flag", rationale="r",
    )
    brand = _rule(rule_id="BRAND-001", category="brand-identity")
    assert rules_for_lens(STRUCTURE, [vision_hier, det_hier, brand]) == [vision_hier]


def test_merge_any_confident_fail_wins():
    merged = merge_lens_verdicts(
        {
            "structure": [{"rule_id": "HIER-001", "status": "pass", "evidence": "hero dominates", "confidence": 0.9}],
            "craft": [{"rule_id": "HIER-001", "status": "fail", "evidence": "two competing CTAs", "confidence": 0.8}],
        },
        [_rule()],
    )
    assert merged[0].status == "fail"
    assert "[craft]" in merged[0].evidence


def test_merge_low_confidence_fail_does_not_block():
    merged = merge_lens_verdicts(
        {
            "structure": [{"rule_id": "HIER-001", "status": "pass", "evidence": "clear", "confidence": 0.9}],
            "craft": [{"rule_id": "HIER-001", "status": "fail", "evidence": "maybe?", "confidence": 0.3}],
        },
        [_rule()],
    )
    assert merged[0].status == "pass"


def test_merge_missing_verdict_is_na_not_pass():
    merged = merge_lens_verdicts({"structure": []}, [_rule()])
    assert merged[0].status == "n/a"


def test_merge_applies_waivers_visibly():
    waiver = Waiver(
        rule_id="HIER-001", scope="kaicalls-*",
        rationale="Split hero is a deliberate A/B experiment this quarter.",
        expires=date(2027, 1, 1), approved_by="connor",
    )
    merged = merge_lens_verdicts(
        {"craft": [{"rule_id": "HIER-001", "status": "fail", "evidence": "two heroes", "confidence": 0.9}]},
        [_rule()],
        target_id="kaicalls-homepage",
        waivers=[waiver],
    )
    assert merged[0].status == "waived"
    assert "A/B experiment" in merged[0].evidence


def test_merge_ignores_invented_rule_ids():
    merged = merge_lens_verdicts(
        {"craft": [{"rule_id": "FAKE-999", "status": "fail", "evidence": "?", "confidence": 0.9}]},
        [_rule()],
    )
    assert [v.rule_id for v in merged] == ["HIER-001"]
    assert merged[0].status == "n/a"
