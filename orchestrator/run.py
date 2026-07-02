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

    NOTE: submit_item/finalize_item are the injection points for gate.submit/gate.finalize.
    gate.py's build_approval_item folds run_date into its dedup_key
    (f"design-os:{target_id}:{run_date}") so that repeated scheduled runs against the same
    target -- design-os's whole purpose -- don't collide with a prior run's approval-inbox
    item via approval_inbox.ApprovalStore.add()'s dedup-idempotent behavior. run_date must be
    supplied by the caller (e.g. datetime.now().date().isoformat()) rather than computed here,
    to keep this dataclass/run_target pure and testable without real datetime calls.
    """

    render: Callable[[Target], Path]
    critique: Callable[[Path], "CritiqueResult"]
    apply_deterministic_fix: Callable[[dict, Path], bool]
    overrides_dir: Path
    submit_item: Callable[[dict], str]
    finalize_item: Callable[[str], None]
    gate_for: Callable[[Target], str]
    run_date: str
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
    below_threshold = critique.composite_score < deps.pass_threshold
    iteration_capped = iterations >= max_iterations and below_threshold
    preview = f"Would ship design review for {target.id} (score {critique.composite_score}/30)."
    item = build_approval_item(
        target.id, critique, gate=gate, dry_run_preview=preview, run_date=deps.run_date
    )
    if below_threshold:
        item["risk_tier"] = "medium"
        if iteration_capped:
            item["summary"] += " Iteration-capped: not all findings resolved."
        else:
            item["summary"] += " Exhausted available fixes: not all findings resolved."
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
