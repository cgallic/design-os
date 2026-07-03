"""Load and validate the design-rule catalog and its waivers.

The catalog (design_os/rules/catalog.yaml) is the enforcement contract distilled
from the canon (design_os/canon/*.md). Validation here is strict on purpose:
a rule that can't be argued mechanically doesn't get to block anything, and a
waiver without a rationale and an expiry date isn't a waiver — it's drift.
"""
from dataclasses import dataclass, field
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

import yaml

DEFAULT_CATALOG_PATH = Path(__file__).parent / "catalog.yaml"

# behavioral = requires runtime interaction (mid-animation retargeting, focus traps,
# interruptibility) that neither a style snapshot nor a screenshot can observe; these
# rules are documented and surfaced, but no engine executes them yet.
VALID_CHECK_TYPES = ("deterministic", "vision", "process", "behavioral")
VALID_SEVERITIES = ("block", "flag", "advise")
VALID_CATEGORIES = (
    "typography",
    "color",
    "spacing-layout",
    "hierarchy",
    "components-affordance",
    "motion",
    "brand-identity",
    "content-information",
    "accessibility",
    "process-workflow",
    "craft-detail",
)
ID_PREFIXES = (
    "TYPE",
    "COLOR",
    "SPACE",
    "HIER",
    "COMP",
    "MOTION",
    "BRAND",
    "INFO",
    "A11Y",
    "PROC",
    "CRAFT",
)


class CatalogError(ValueError):
    """The catalog or waiver file violates the harness contract."""


# Artifact scopes a rule may declare via applies_to. "any" (the default) fires on
# every audit; everything else only fires when the run declares a matching artifact
# type — so identity-only or dashboard-only blocks can't misfire on a page audit,
# and org/project ceremony gates never block artifact evaluation at all.
VALID_APPLIES_TO = (
    "any",
    "page",
    "dashboard",
    "chart",
    "identity",
    "print",
    "flow",
    "project",
    "org",
)


@dataclass(frozen=True)
class Rule:
    id: str
    statement: str
    category: str
    check_type: str
    threshold: str
    severity: str
    rationale: str
    sources: tuple[str, ...] = ()
    tension: str = ""
    applies_to: tuple[str, ...] = ("any",)


@dataclass(frozen=True)
class Waiver:
    rule_id: str
    scope: str  # target id or fnmatch glob ("kaicalls-*"); "*" is deliberately rejected
    rationale: str
    expires: date
    approved_by: str


def _validate_rule(raw: dict, seen_ids: set[str]) -> Rule:
    for key in ("id", "statement", "category", "check_type", "severity", "rationale"):
        if not raw.get(key):
            raise CatalogError(f"rule {raw.get('id', '<no id>')!r}: missing required field {key!r}")
    rule_id = raw["id"]
    if rule_id in seen_ids:
        raise CatalogError(f"duplicate rule id {rule_id!r}")
    prefix, _, num = rule_id.partition("-")
    if prefix not in ID_PREFIXES or not (num.isdigit() and len(num) == 3):
        raise CatalogError(f"rule id {rule_id!r} must be <PREFIX>-<3 digits> with prefix in {ID_PREFIXES}")
    if raw["check_type"] not in VALID_CHECK_TYPES:
        raise CatalogError(f"rule {rule_id}: check_type {raw['check_type']!r} not in {VALID_CHECK_TYPES}")
    if raw["severity"] not in VALID_SEVERITIES:
        raise CatalogError(f"rule {rule_id}: severity {raw['severity']!r} not in {VALID_SEVERITIES}")
    if raw["category"] not in VALID_CATEGORIES:
        raise CatalogError(f"rule {rule_id}: category {raw['category']!r} not in {VALID_CATEGORIES}")
    threshold = str(raw.get("threshold", "") or "")
    if raw["check_type"] == "deterministic" and not threshold.strip():
        raise CatalogError(
            f"rule {rule_id}: deterministic rules must carry a threshold — "
            "a deterministic check with nothing to compute against is a vibe, not a rule"
        )
    if raw["severity"] == "block" and raw["check_type"] != "process" and not threshold.strip():
        raise CatalogError(
            f"rule {rule_id}: a 'block' rule must be mechanically arguable — give it a threshold "
            "or an enumerable criterion, or downgrade it to 'flag'"
        )
    applies_to = tuple(raw.get("applies_to") or ("any",))
    bad_scopes = [s for s in applies_to if s not in VALID_APPLIES_TO]
    if bad_scopes:
        raise CatalogError(f"rule {rule_id}: applies_to values {bad_scopes} not in {VALID_APPLIES_TO}")
    return Rule(
        id=rule_id,
        statement=str(raw["statement"]).strip(),
        category=raw["category"],
        check_type=raw["check_type"],
        threshold=threshold.strip(),
        severity=raw["severity"],
        rationale=str(raw["rationale"]).strip(),
        sources=tuple(raw.get("sources") or ()),
        tension=str(raw.get("tension", "") or "").strip(),
        applies_to=applies_to,
    )


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> list[Rule]:
    """Load and strictly validate the rule catalog. Raises CatalogError on any violation."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise CatalogError(f"{path}: catalog must be a mapping with a top-level 'rules' list")
    rules: list[Rule] = []
    seen: set[str] = set()
    for raw in data["rules"]:
        rule = _validate_rule(raw, seen)
        seen.add(rule.id)
        rules.append(rule)
    if not rules:
        raise CatalogError(f"{path}: catalog contains no rules")
    return rules


def applicable_rules(rules: list[Rule], artifact_type: str) -> list[Rule]:
    """Rules that fire for an artifact of the given type: scope 'any' always fires;
    other scopes require an exact match. Audit-only page runs should pass 'page'."""
    if artifact_type not in VALID_APPLIES_TO:
        raise CatalogError(f"unknown artifact type {artifact_type!r}; expected one of {VALID_APPLIES_TO}")
    return [r for r in rules if "any" in r.applies_to or artifact_type in r.applies_to]


def load_waivers(path: Path, known_rule_ids: set[str], today: date) -> list[Waiver]:
    """Load waivers.yaml. Expired, blanket, or under-justified waivers are hard errors:
    a waiver file that silently rots is worse than no waiver system at all."""
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_waivers = data.get("waivers")
    if not isinstance(raw_waivers, list):
        raise CatalogError(f"{path}: waiver file must have a top-level 'waivers' list")
    waivers: list[Waiver] = []
    for raw in raw_waivers:
        for key in ("rule_id", "scope", "rationale", "expires", "approved_by"):
            if not raw.get(key):
                raise CatalogError(f"waiver for {raw.get('rule_id', '<no rule>')!r}: missing {key!r}")
        if raw["rule_id"] not in known_rule_ids:
            raise CatalogError(f"waiver references unknown rule {raw['rule_id']!r}")
        if raw["scope"].strip() == "*":
            raise CatalogError(
                f"waiver for {raw['rule_id']}: scope '*' is a policy change, not a waiver — "
                "edit the catalog instead"
            )
        if len(str(raw["rationale"]).split()) < 5:
            raise CatalogError(
                f"waiver for {raw['rule_id']}: rationale must actually explain the intent "
                "(>= 5 words) — 'looks better' is not a rationale"
            )
        expires = raw["expires"]
        if isinstance(expires, str):
            expires = date.fromisoformat(expires)
        if not isinstance(expires, date):
            raise CatalogError(f"waiver for {raw['rule_id']}: 'expires' must be an ISO date")
        if expires < today:
            raise CatalogError(
                f"waiver for {raw['rule_id']} expired {expires.isoformat()} — renew it with a "
                "fresh rationale or delete it"
            )
        waivers.append(
            Waiver(
                rule_id=raw["rule_id"],
                scope=str(raw["scope"]).strip(),
                rationale=str(raw["rationale"]).strip(),
                expires=expires,
                approved_by=str(raw["approved_by"]).strip(),
            )
        )
    return waivers


def active_waiver_for(rule_id: str, target_id: str, waivers: list[Waiver]) -> Waiver | None:
    """Return the waiver covering (rule_id, target_id), if any. Scope is exact or fnmatch glob."""
    for waiver in waivers:
        if waiver.rule_id == rule_id and fnmatch(target_id, waiver.scope):
            return waiver
    return None
