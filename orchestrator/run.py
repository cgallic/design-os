"""Drive one design-os pass for a single target: render -> critique -> repair -> gate."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from critique.repair_ops import classify_finding
from gate import build_approval_item
from orchestrator.signals import Target


@dataclass
class RunDeps:
    """Injectable dependencies for run_target, so control flow is testable without real
    subprocesses or a real approval-inbox store.

    NOTE (caveat for whoever wires real dependencies together, e.g. Task 10):
    submit_item/finalize_item are the injection points for gate.submit/gate.finalize.
    gate.py's build_approval_item always generates a fixed dedup_key of
    f"design-os:{target_id}" with no per-run variation, and approval_inbox.ApprovalStore.add()
    is dedup-idempotent on dedup_key (a second .add() with the same key returns the FIRST
    item's id rather than creating a new one). If submit_item/finalize_item are ever wired to
    the real gate.submit/gate.finalize and run_target is invoked more than once for the same
    target -- including across separate scheduled runs, which is design-os's whole purpose --
    the second run's finalize_item call could raise approval_inbox.StateError if the first
    item already reached a terminal execution_state. Callers wiring real dependencies must
    either make dedup_key vary per run (e.g. include a date or run id) or check
    execution_state before finalize on repeat runs for the same target. Not fixed here --
    this dataclass only documents the caveat; see gate.py's fixed dedup_key format.
    """

    render: Callable[[Target], Path]
    critique: Callable[[Path], "CritiqueResult"]
    apply_deterministic_fix: Callable[[dict, Path], bool]
    overrides_dir: Path
    submit_item: Callable[[dict], str]
    finalize_item: Callable[[str], None]
    gate_for: Callable[[Target], str]
    pass_threshold: int = 25


def run_target(target: Target, deps: RunDeps, max_iterations: int = 3) -> dict:
    """Run render->critique->repair up to max_iterations times, then gate the result."""
    overrides_path = deps.overrides_dir / f"{target.id}-overrides.css"
    iterations = 0
    critique = None
    for iterations in range(1, max_iterations + 1):
        run_dir = deps.render(target)
        critique = deps.critique(run_dir)
        if critique.composite_score >= deps.pass_threshold:
            break
        deterministic_fixes_applied = 0
        for finding in critique.prioritized_fixes:
            if finding["priority"] not in ("P0", "P1"):
                continue
            fix_type = classify_finding(finding)
            if fix_type != "flag":
                deps.apply_deterministic_fix(finding, overrides_path)
                deterministic_fixes_applied += 1
        if deterministic_fixes_applied == 0:
            break  # nothing left we can fix automatically; stop early rather than burn iterations

    gate = deps.gate_for(target)
    capped = iterations >= max_iterations and critique.composite_score < deps.pass_threshold
    preview = f"Would ship design review for {target.id} (score {critique.composite_score}/30)."
    item = build_approval_item(target.id, critique, gate=gate, dry_run_preview=preview)
    if capped:
        item["risk_tier"] = "medium"
        item["summary"] += " Iteration-capped: not all findings resolved."
    item_id = deps.submit_item(item)
    deps.finalize_item(item_id)

    return {
        "target_id": target.id,
        "final_score": critique.composite_score,
        "iterations": iterations,
        "gate": gate,
        "item_id": item_id,
    }


def main() -> None:
    import argparse
    from datetime import datetime, timedelta
    from orchestrator.signals import load_watchlist
    from orchestrator.detect import due_targets

    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Print due targets without running the pipeline.")
    args = parser.parse_args()

    targets = load_watchlist(args.watchlist)
    due = due_targets(targets, last_run={}, now=datetime.now(), sweep_interval=timedelta(days=7))

    if args.dry_run:
        for target in due:
            print(f"DUE: {target.id}")
        return

    raise NotImplementedError(
        "Live run wiring (real RunDeps with run_qa/run_vision_critique/ApprovalStore) "
        "is an infrastructure task, not a unit-testable code path — see deploy/README.md."
    )


if __name__ == "__main__":
    main()
