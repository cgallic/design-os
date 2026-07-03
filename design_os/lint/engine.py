"""Run deterministic rule checks against a style snapshot.

bindings.yaml maps catalog rule IDs to check implementations in checks.py:

bindings:
  - rule_id: A11Y-001
    check: contrast_min
    params: {ratio_normal: 4.5, ratio_large: 3.0}

Deterministic rules with no binding surface as status="unimplemented" rather
than disappearing — an honest gap report is part of the harness contract.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import yaml

from design_os.lint.checks import CHECKS
from design_os.rules.loader import Rule, Waiver, active_waiver_for

DEFAULT_BINDINGS_PATH = Path(__file__).parent / "bindings.yaml"


@dataclass(frozen=True)
class Verdict:
    rule_id: str
    status: str  # pass | fail | n/a | unimplemented | waived
    evidence: str
    severity: str
    source: str = "lint"  # lint | vision | process

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Binding:
    rule_id: str
    check: str
    params: dict


def load_bindings(path: Path = DEFAULT_BINDINGS_PATH) -> list[Binding]:
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    bindings = []
    for raw in data.get("bindings", []):
        check = raw.get("check", "")
        if check not in CHECKS:
            raise ValueError(f"binding for {raw.get('rule_id')}: unknown check {check!r} (have: {sorted(CHECKS)})")
        bindings.append(Binding(rule_id=raw["rule_id"], check=check, params=dict(raw.get("params") or {})))
    return bindings


def run_lint(
    snapshot: dict,
    rules: list[Rule],
    bindings: list[Binding],
    target_id: str = "",
    waivers: list[Waiver] | None = None,
) -> list[Verdict]:
    """Evaluate every deterministic rule: bound rules run their check; unbound ones
    report as unimplemented; waived failures downgrade to status='waived' with the
    waiver rationale as evidence (visible, never silent)."""
    waivers = waivers or []
    by_id = {b.rule_id: b for b in bindings}
    verdicts: list[Verdict] = []
    for rule in rules:
        if rule.check_type != "deterministic":
            continue
        binding = by_id.get(rule.id)
        if binding is None:
            verdicts.append(
                Verdict(rule.id, "unimplemented", "no deterministic check bound to this rule yet", rule.severity)
            )
            continue
        status, evidence = CHECKS[binding.check](snapshot, **binding.params)
        if status == "fail":
            waiver = active_waiver_for(rule.id, target_id, waivers)
            if waiver is not None:
                status = "waived"
                evidence = (
                    f"failed ({evidence}) but waived for scope {waiver.scope!r} "
                    f"until {waiver.expires.isoformat()}: {waiver.rationale}"
                )
        verdicts.append(Verdict(rule.id, status, evidence, rule.severity))
    return verdicts


def blocking_failures(verdicts: list[Verdict]) -> list[Verdict]:
    return [v for v in verdicts if v.status == "fail" and v.severity == "block"]
