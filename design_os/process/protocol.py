"""The design process protocol: stage gates over a process log.

Any agent (or human) doing design work under design-os keeps a process log — a
plain YAML/JSON dict recording what actually happened at each stage. This module
validates that log against the protocol. The stages encode the workflow
practices of the canon (divergence before convergence, taste contracts instead
of adjectives, critique before ship), and validation is mechanical: a stage
either carries the required evidence or it doesn't.

The protocol constrains the *shape* of the work, never its content — that is
the creative-flexibility line. It never says "make it minimal"; it says "show
me three directions before you pick one."

Process log shape (YAML):

target: kaicalls-homepage
stages:
  brief:
    problem: "..."
    audience: "..."
    constraints:            # the taste contract — testable, not adjectives
      - "hero renders complete headline at 375px without wrapping past 3 lines"
    banned_adjective_check: true
  divergence:
    directions:
      - {name: "...", premise: "...", artifact: "path-or-url"}
      - {name: "...", premise: "...", artifact: "path-or-url"}
      - {name: "...", premise: "...", artifact: "path-or-url"}
  convergence:
    chosen: "..."
    why: "..."
    killed:
      - {name: "...", why: "..."}
  build:
    tokens_source: "path to the token set actually used"
    components_reused: [...]
    components_invented: [...]     # each invention needs a reason
    invention_reasons: {"<component>": "why nothing existing worked"}
  self_lint:
    snapshot: "path to style snapshot"
    unwaived_block_failures: 0
  critique:
    lenses_run: [structure, craft, brand]
    verdicts: "path to merged verdicts"
    fails_addressed: true
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# Adjectives that are banned as *constraints*. They are fine in prose; they are
# not fine as the load-bearing content of a taste contract, because nothing can
# fail against them.
BANNED_CONSTRAINT_ADJECTIVES = (
    "clean",
    "modern",
    "sleek",
    "beautiful",
    "elegant",
    "premium",
    "minimal",
    "professional",
    "fresh",
    "polished",
    "stunning",
    "delightful",
)

MIN_DIVERGENT_DIRECTIONS = 3


class ProcessError(ValueError):
    pass


@dataclass(frozen=True)
class StageResult:
    stage: str
    ok: bool
    problems: tuple[str, ...]


def _check_brief(stage: dict) -> list[str]:
    problems = []
    for key in ("problem", "audience"):
        if not str(stage.get(key, "")).strip():
            problems.append(f"brief.{key} is empty — you cannot design toward an unstated {key}")
    constraints = stage.get("constraints") or []
    if len(constraints) < 3:
        problems.append(
            f"brief.constraints has {len(constraints)} entries (need >= 3): the taste contract "
            "is the brief's spine — without testable constraints, critique has nothing to bite on"
        )
    for constraint in constraints:
        words = {w.strip(".,;:").lower() for w in str(constraint).split()}
        hits = words & set(BANNED_CONSTRAINT_ADJECTIVES)
        # An adjective may appear, but not carry the constraint alone: a constraint is
        # exempt if it contains a digit or a comparator (a checkable core).
        has_checkable_core = any(ch.isdigit() for ch in str(constraint)) or any(
            tok in str(constraint) for tok in ("<=", ">=", "<", ">", "==", "within", "at least", "at most", "no more", "never", "always", "every", "must")
        )
        if hits and not has_checkable_core:
            problems.append(
                f"brief constraint {str(constraint)!r} leans on banned adjective(s) {sorted(hits)} "
                "with no checkable core — restate it as something that can fail"
            )
    return problems


def _check_divergence(stage: dict) -> list[str]:
    problems = []
    directions = stage.get("directions") or []
    if len(directions) < MIN_DIVERGENT_DIRECTIONS:
        problems.append(
            f"divergence produced {len(directions)} directions (need >= {MIN_DIVERGENT_DIRECTIONS}): "
            "one idea is a guess, two is a coin flip, three is a search"
        )
    premises = [str(d.get("premise", "")).strip().lower() for d in directions]
    if len(set(p for p in premises if p)) < len(directions):
        problems.append("divergent directions share a premise — variations on one idea are not divergence")
    for direction in directions:
        if not str(direction.get("artifact", "")).strip():
            problems.append(
                f"direction {direction.get('name', '?')!r} has no artifact — an unrendered idea was never explored"
            )
    return problems


def _check_convergence(stage: dict) -> list[str]:
    problems = []
    if not str(stage.get("chosen", "")).strip():
        problems.append("convergence.chosen is empty")
    if not str(stage.get("why", "")).strip():
        problems.append("convergence.why is empty — a choice without a reason cannot be reviewed")
    killed = stage.get("killed") or []
    if not killed:
        problems.append("convergence.killed is empty — if nothing was killed, nothing was compared")
    for kill in killed:
        if not str(kill.get("why", "")).strip():
            problems.append(f"killed direction {kill.get('name', '?')!r} has no stated reason")
    return problems


def _check_build(stage: dict) -> list[str]:
    problems = []
    if not str(stage.get("tokens_source", "")).strip():
        problems.append("build.tokens_source is empty — building off-token is how cohesion dies")
    invented = stage.get("components_invented") or []
    reasons = stage.get("invention_reasons") or {}
    for component in invented:
        if not str(reasons.get(component, "")).strip():
            problems.append(
                f"invented component {component!r} has no invention_reason — reuse is the default; "
                "invention must argue for itself"
            )
    return problems


def _check_self_lint(stage: dict) -> list[str]:
    problems = []
    if not str(stage.get("snapshot", "")).strip():
        problems.append("self_lint.snapshot is empty — the lint stage did not run")
    failures = stage.get("unwaived_block_failures")
    if failures is None:
        problems.append("self_lint.unwaived_block_failures missing")
    elif int(failures) > 0:
        problems.append(f"self_lint reports {failures} unwaived block failure(s) — fix or waive before critique")
    return problems


def _check_critique(stage: dict) -> list[str]:
    problems = []
    lenses = stage.get("lenses_run") or []
    if len(lenses) < 2:
        problems.append(f"critique ran {len(lenses)} lens(es) (need >= 2): one pair of eyes is not a critique")
    if not str(stage.get("verdicts", "")).strip():
        problems.append("critique.verdicts is empty — critique without a record didn't happen")
    if stage.get("fails_addressed") is not True:
        problems.append("critique.fails_addressed is not true — every fail is fixed, waived, or argued, never ignored")
    return problems


STAGES: dict[str, Callable[[dict], list[str]]] = {
    "brief": _check_brief,
    "divergence": _check_divergence,
    "convergence": _check_convergence,
    "build": _check_build,
    "self_lint": _check_self_lint,
    "critique": _check_critique,
}


def validate_process_log(log: dict, required_stages: tuple[str, ...] | None = None) -> list[StageResult]:
    """Validate a process log against the protocol; returns one StageResult per required stage.

    required_stages defaults to all stages. Audit-only runs (design-os watching a live
    URL it didn't design) should pass e.g. ("self_lint", "critique").
    """
    required = required_stages or tuple(STAGES)
    unknown = [s for s in required if s not in STAGES]
    if unknown:
        raise ProcessError(f"unknown stages requested: {unknown}")
    stages = log.get("stages") or {}
    results = []
    for name in required:
        stage = stages.get(name)
        if stage is None:
            results.append(StageResult(name, False, (f"stage {name!r} missing from process log",)))
            continue
        problems = STAGES[name](stage)
        results.append(StageResult(name, not problems, tuple(problems)))
    return results
