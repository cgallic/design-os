"""Compile the canon + rule catalog into critique-lens prompts.

A lens is one perspective on the work — a named group of canon schools plus the
catalog categories they police. Each lens prompt embeds the relevant canon text
and the vision-checkable rules verbatim, and demands a per-rule verdict with
evidence. Three lenses looking with different eyes catch what one generic
"critique this" pass smooths over; the structured verdicts are what makes the
output enforceable instead of an essay.

The JSON contract is a strict superset of the kai-taste contract vision.py's
pipeline already parses ("issues" / "working_well" / "scorecard"), adding a
"verdicts" array keyed by catalog rule IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from design_os.lint.engine import Verdict
from design_os.rules.loader import Rule, Waiver, active_waiver_for

DEFAULT_CANON_DIR = Path(__file__).parent.parent / "canon"


@dataclass(frozen=True)
class Lens:
    key: str
    title: str
    schools: tuple[str, ...]  # canon file stems whose full text this lens carries
    categories: tuple[str, ...]  # catalog categories whose vision rules this lens judges


# Three lenses, chosen so every vision-checkable category has exactly one owner:
# a rule judged by all lenses is judged carefully by none.
DEFAULT_LENSES = (
    Lens(
        key="structure",
        title="Structure & Typography — the Swiss eye",
        schools=("swiss-grid", "typography-canon", "refactoring-ui", "system-governance"),
        categories=("typography", "spacing-layout", "hierarchy"),
    ),
    Lens(
        key="craft",
        title="Craft & Interaction — the product-craft eye",
        schools=("interface-craft", "apple-hig", "motion-design", "rams-functionalism", "critique-process"),
        categories=("components-affordance", "motion", "craft-detail", "accessibility"),
    ),
    Lens(
        key="brand",
        title="Brand & Communication — the identity eye",
        schools=("brand-identity", "saas-quality-culture", "information-design"),
        categories=("brand-identity", "content-information", "color"),
    ),
)

_VERDICT_CONTRACT = """
Respond with minified JSON matching this exact shape:
{
  "verdicts": [
    {"rule_id": "<catalog id, e.g. HIER-001>", "status": "pass|fail|n/a", "evidence": "<what you see that proves it — name the element/region>", "confidence": 0.0-1.0}
  ],
  "issues": [
    {"heuristic": "<rule id or failure-mode name>", "description": "...", "evidence": "...", "severity": 0-4, "confidence": 0.0-1.0, "fix": "..."}
  ],
  "working_well": ["..."],
  "scorecard": {
    "pillars": {"deterministic_stochastic_balance": 1-10, "interaction_density": 1-10, "visual_cohesion": 1-10},
    "composite": 3-30,
    "failure_modes_present": ["..."],
    "prioritized_fixes": [{"priority": "P0|P1|P2", "fix": "...", "pillar": "..."}]
  }
}

Verdict discipline:
- Return one verdict for EVERY rule listed above — no skipping. Use "n/a" only when
  the rule's subject genuinely does not appear in the screenshot (say why).
- "fail" requires visible evidence you can point to. If you cannot name the element,
  it is not a fail.
- Do not soften: a rule that fails, fails, even if the overall design is good.
- Do not invent rules; judge only what is listed.
""".strip()


def _read_canon(canon_dir: Path, school: str) -> str | None:
    path = Path(canon_dir) / f"{school}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def rules_for_lens(lens: Lens, rules: list[Rule]) -> list[Rule]:
    return [r for r in rules if r.check_type == "vision" and r.category in lens.categories]


def build_lens_prompt(
    lens: Lens,
    rules: list[Rule],
    canon_dir: Path = DEFAULT_CANON_DIR,
    screenshot_instruction: str = "",
) -> str:
    """Compose one lens's critique prompt. Raises if the lens has no rules to judge —
    an empty lens silently passing everything is exactly the failure this harness exists
    to prevent."""
    lens_rules = rules_for_lens(lens, rules)
    if not lens_rules:
        raise ValueError(f"lens {lens.key!r}: no vision rules in categories {lens.categories}")
    canon_sections = []
    for school in lens.schools:
        text = _read_canon(canon_dir, school)
        if text:
            canon_sections.append(text)
    rule_lines = "\n".join(
        f"- [{r.id}] ({r.severity.upper()}) {r.statement}"
        + (f" Threshold: {r.threshold}." if r.threshold else "")
        + f" — {r.rationale}"
        for r in lens_rules
    )
    parts = [
        f"You are a design critic auditing a rendered screenshot through one specific lens: {lens.title}.",
        "You judge ONLY the rules listed below. Other lenses cover everything else — do not drift.",
        screenshot_instruction,
        "## The canon behind this lens\n\n" + "\n\n---\n\n".join(canon_sections)
        if canon_sections
        else "",
        "## Rules to judge (verdict required for each)\n\n" + rule_lines,
        _VERDICT_CONTRACT,
    ]
    return "\n\n".join(p for p in parts if p)


def merge_lens_verdicts(
    per_lens_verdicts: dict[str, list[dict]],
    rules: list[Rule],
    target_id: str = "",
    waivers: list[Waiver] | None = None,
    fail_confidence: float = 0.6,
) -> list[Verdict]:
    """Merge raw verdict dicts from N lens passes into one Verdict per vision rule.

    A rule fails if any lens fails it with confidence >= fail_confidence; passes if
    at least one lens passed it and none failed; n/a otherwise. Waivers downgrade
    fails to 'waived' with the rationale kept visible.
    """
    waivers = waivers or []
    by_rule = {r.id: r for r in rules if r.check_type == "vision"}
    collected: dict[str, list[tuple[str, dict]]] = {}
    for lens_key, verdicts in per_lens_verdicts.items():
        for raw in verdicts:
            rule_id = raw.get("rule_id", "")
            if rule_id in by_rule:
                collected.setdefault(rule_id, []).append((lens_key, raw))

    merged: list[Verdict] = []
    for rule_id, rule in by_rule.items():
        entries = collected.get(rule_id, [])
        fails = [
            (lens, raw)
            for lens, raw in entries
            if raw.get("status") == "fail" and float(raw.get("confidence", 0)) >= fail_confidence
        ]
        passes = [(lens, raw) for lens, raw in entries if raw.get("status") == "pass"]
        if fails:
            lens, raw = fails[0]
            status = "fail"
            evidence = f"[{lens}] {raw.get('evidence', '')}"
            waiver = active_waiver_for(rule_id, target_id, waivers)
            if waiver is not None:
                status = "waived"
                evidence = (
                    f"failed ({evidence}) but waived for scope {waiver.scope!r} "
                    f"until {waiver.expires.isoformat()}: {waiver.rationale}"
                )
        elif passes:
            status, evidence = "pass", f"[{passes[0][0]}] {passes[0][1].get('evidence', '')}"
        elif entries:
            status, evidence = "n/a", f"[{entries[0][0]}] {entries[0][1].get('evidence', '')}"
        else:
            status, evidence = "n/a", "no lens returned a verdict for this rule"
        merged.append(Verdict(rule_id, status, evidence, rule.severity, source="vision"))
    return merged
