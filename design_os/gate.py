"""Submit design-os critique results to approval-inbox, gated safe/irreversible."""
from design_os.critique.runner import CritiqueResult


def build_approval_item(
    target_id: str, critique: CritiqueResult, gate: str, dry_run_preview: str, run_date: str
) -> dict:
    """Build an ApprovalStore.add()-ready item dict from a critique result.

    gate: "safe" (draft-only output, auto-approved) or "irreversible" (touches a live surface, held for a human).
    run_date: caller-supplied date string (e.g. datetime.now().date().isoformat()) folded into
    dedup_key so repeated scheduled runs against the same target_id don't collide with a prior
    run's approval-inbox item (see ApprovalStore.add()'s dedup-idempotent behavior).
    """
    owner = "agent-auto" if gate == "safe" else "approve"
    risk_tier = "low" if gate == "safe" else "high"
    evidence = [
        {"label": "composite_score", "value": str(critique.composite_score)},
        {"label": "open_p0_fixes", "value": str(sum(1 for f in critique.prioritized_fixes if f["priority"] == "P0"))},
    ]
    return {
        "type": "task",
        "channel": "design",
        "source": "design-os",
        "title": f"Design review: {target_id}",
        "summary": f"kai-taste composite score {critique.composite_score}/30, "
        f"{len(critique.prioritized_fixes)} prioritized fixes.",
        "owner": owner,
        "gate": gate,
        "risk_tier": risk_tier,
        "evidence": evidence,
        "action": {"kind": "design.publish", "params": {"target_id": target_id}, "dry_run_preview": dry_run_preview},
        "dedup_key": f"design-os:{target_id}:{run_date}",
    }


def submit(store, item: dict) -> str:
    """Add an item to the approval-inbox store; returns its id."""
    return store.add(item)


def finalize(store, item_id: str) -> None:
    """Auto-execute safe items; leave irreversible items pending for a human."""
    item = store.get(item_id)
    if item["gate"] == "safe":
        store.transition(item_id, "agent_do", actor="agent-auto")
