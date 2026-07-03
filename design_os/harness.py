"""The harness spine: combine lint, lens-panel, and process verdicts into one report
and one gate decision.

The contract, in one sentence: nothing with an unwaived 'block' failure ever
auto-ships — it is fixed, waived (visibly, with a rationale and an expiry), or a
human approves it eyes-open. Everything below 'block' informs; it never gates.
That split is what keeps the harness strict without strangling creative range:
blocks are few and mechanically arguable, flags and advice are plentiful and
free to ignore with judgment.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from design_os.lint.engine import Verdict
from design_os.process.protocol import StageResult


@dataclass
class HarnessReport:
    target_id: str
    lint_verdicts: list[Verdict] = field(default_factory=list)
    vision_verdicts: list[Verdict] = field(default_factory=list)
    process_results: list[StageResult] = field(default_factory=list)

    @property
    def verdicts(self) -> list[Verdict]:
        return self.lint_verdicts + self.vision_verdicts

    def blocking_failures(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.status == "fail" and v.severity == "block"]

    def failed_process_stages(self) -> list[StageResult]:
        return [r for r in self.process_results if not r.ok]

    def counts(self) -> dict:
        counts = {"pass": 0, "fail": 0, "n/a": 0, "waived": 0, "unimplemented": 0}
        for v in self.verdicts:
            counts[v.status] = counts.get(v.status, 0) + 1
        return counts


def gate_decision(base_gate: str, report: HarnessReport) -> str:
    """A run with unwaived block failures (or failed process gates) is held for a human
    regardless of how safe the surface is: 'safe to ship mechanically' is not the same
    as 'fit to ship'."""
    if report.blocking_failures() or report.failed_process_stages():
        return "irreversible"
    return base_gate


def evidence_rows(report: HarnessReport) -> list[dict]:
    """Approval-inbox evidence rows summarizing the harness verdicts."""
    counts = report.counts()
    rows = [
        {"label": "rules_checked", "value": str(len(report.verdicts))},
        {"label": "rules_failed", "value": str(counts["fail"])},
        {"label": "rules_waived", "value": str(counts["waived"])},
        {"label": "rules_unimplemented", "value": str(counts["unimplemented"])},
    ]
    blockers = report.blocking_failures()
    if blockers:
        rows.append(
            {
                "label": "blocking_failures",
                "value": "; ".join(f"{v.rule_id}: {v.evidence}"[:160] for v in blockers[:8]),
            }
        )
    for stage in report.failed_process_stages():
        rows.append({"label": f"process_gate_{stage.stage}", "value": "; ".join(stage.problems)[:300]})
    return rows
