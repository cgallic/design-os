from datetime import date
from pathlib import Path

import pytest

from design_os.rules.loader import (
    CatalogError,
    active_waiver_for,
    applicable_rules,
    load_catalog,
    load_waivers,
)


def _write_catalog(tmp_path: Path, rules_yaml: str) -> Path:
    path = tmp_path / "catalog.yaml"
    path.write_text(f"version: 1\nrules:\n{rules_yaml}", encoding="utf-8")
    return path


GOOD_RULE = """
  - id: TYPE-001
    statement: Body text is at least 16px.
    category: typography
    check_type: deterministic
    threshold: ">= 16px"
    severity: flag
    rationale: Butterick, Practical Typography.
    sources: [typography-canon]
"""


def test_load_catalog_happy_path(tmp_path):
    rules = load_catalog(_write_catalog(tmp_path, GOOD_RULE))
    assert len(rules) == 1
    assert rules[0].id == "TYPE-001"
    assert rules[0].sources == ("typography-canon",)


def test_duplicate_ids_rejected(tmp_path):
    with pytest.raises(CatalogError, match="duplicate"):
        load_catalog(_write_catalog(tmp_path, GOOD_RULE + GOOD_RULE))


def test_deterministic_rule_without_threshold_rejected(tmp_path):
    bad = GOOD_RULE.replace('threshold: ">= 16px"', 'threshold: ""')
    with pytest.raises(CatalogError, match="threshold"):
        load_catalog(_write_catalog(tmp_path, bad))


def test_block_without_threshold_rejected(tmp_path):
    bad = """
  - id: HIER-001
    statement: The page has one dominant focal point.
    category: hierarchy
    check_type: vision
    threshold: ""
    severity: block
    rationale: Somebody said so.
"""
    with pytest.raises(CatalogError, match="mechanically arguable"):
        load_catalog(_write_catalog(tmp_path, bad))


def test_process_block_without_threshold_allowed(tmp_path):
    ok = """
  - id: PROC-001
    statement: Present at least 3 divergent directions before converging.
    category: process-workflow
    check_type: process
    threshold: ""
    severity: block
    rationale: Divergence before convergence.
"""
    rules = load_catalog(_write_catalog(tmp_path, ok))
    assert rules[0].severity == "block"


def test_bad_id_prefix_rejected(tmp_path):
    bad = GOOD_RULE.replace("TYPE-001", "FONT-001")
    with pytest.raises(CatalogError, match="prefix"):
        load_catalog(_write_catalog(tmp_path, bad))


SCOPED_RULES = GOOD_RULE + """
  - id: BRAND-001
    statement: An onliness statement exists for the brand.
    category: brand-identity
    check_type: process
    threshold: ""
    severity: block
    rationale: Neumeier.
    applies_to: [identity, project]
  - id: MOTION-006
    statement: Animations are interruptible mid-flight.
    category: motion
    check_type: behavioral
    threshold: "retarget within 1 frame"
    severity: flag
    rationale: Interface craft.
"""


def test_applies_to_scoping(tmp_path):
    rules = load_catalog(_write_catalog(tmp_path, SCOPED_RULES))
    page_rules = applicable_rules(rules, "page")
    assert [r.id for r in page_rules] == ["TYPE-001", "MOTION-006"]  # default 'any' fires everywhere
    identity_rules = applicable_rules(rules, "identity")
    assert "BRAND-001" in [r.id for r in identity_rules]


def test_unknown_artifact_type_rejected(tmp_path):
    rules = load_catalog(_write_catalog(tmp_path, GOOD_RULE))
    with pytest.raises(CatalogError, match="artifact type"):
        applicable_rules(rules, "vibes")


def test_bad_applies_to_value_rejected(tmp_path):
    bad = GOOD_RULE.replace("sources: [typography-canon]", "applies_to: [everything]")
    with pytest.raises(CatalogError, match="applies_to"):
        load_catalog(_write_catalog(tmp_path, bad))


def test_behavioral_check_type_accepted(tmp_path):
    rules = load_catalog(_write_catalog(tmp_path, SCOPED_RULES))
    assert any(r.check_type == "behavioral" for r in rules)


def _write_waivers(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "waivers.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_waiver_happy_path_and_scope_matching(tmp_path):
    path = _write_waivers(
        tmp_path,
        """
waivers:
  - rule_id: TYPE-001
    scope: "kaicalls-*"
    rationale: Marketing hero uses display type at 14px deliberately for the badge row.
    expires: 2027-01-01
    approved_by: connor
""",
    )
    waivers = load_waivers(path, {"TYPE-001"}, today=date(2026, 7, 3))
    assert active_waiver_for("TYPE-001", "kaicalls-homepage", waivers) is not None
    assert active_waiver_for("TYPE-001", "other-site", waivers) is None
    assert active_waiver_for("TYPE-002", "kaicalls-homepage", waivers) is None


def test_expired_waiver_is_a_hard_error(tmp_path):
    path = _write_waivers(
        tmp_path,
        """
waivers:
  - rule_id: TYPE-001
    scope: kaicalls-homepage
    rationale: Temporary exemption during the brand refresh sprint only.
    expires: 2026-01-01
    approved_by: connor
""",
    )
    with pytest.raises(CatalogError, match="expired"):
        load_waivers(path, {"TYPE-001"}, today=date(2026, 7, 3))


def test_blanket_waiver_rejected(tmp_path):
    path = _write_waivers(
        tmp_path,
        """
waivers:
  - rule_id: TYPE-001
    scope: "*"
    rationale: We simply do not like this rule at all.
    expires: 2027-01-01
    approved_by: connor
""",
    )
    with pytest.raises(CatalogError, match="policy change"):
        load_waivers(path, {"TYPE-001"}, today=date(2026, 7, 3))


def test_thin_rationale_rejected(tmp_path):
    path = _write_waivers(
        tmp_path,
        """
waivers:
  - rule_id: TYPE-001
    scope: kaicalls-homepage
    rationale: looks better
    expires: 2027-01-01
    approved_by: connor
""",
    )
    with pytest.raises(CatalogError, match="rationale"):
        load_waivers(path, {"TYPE-001"}, today=date(2026, 7, 3))


def test_unknown_rule_waiver_rejected(tmp_path):
    path = _write_waivers(
        tmp_path,
        """
waivers:
  - rule_id: TYPE-999
    scope: kaicalls-homepage
    rationale: This rule id does not exist in the catalog.
    expires: 2027-01-01
    approved_by: connor
""",
    )
    with pytest.raises(CatalogError, match="unknown rule"):
        load_waivers(path, {"TYPE-001"}, today=date(2026, 7, 3))


def test_missing_waiver_file_is_empty(tmp_path):
    assert load_waivers(tmp_path / "nope.yaml", {"TYPE-001"}, today=date(2026, 7, 3)) == []
