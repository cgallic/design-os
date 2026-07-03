"""Standalone lint: `python -m design_os.lint <url> [--target-id ID] [--waivers waivers.yaml]`

Extracts a live style snapshot and runs every bound deterministic catalog rule
against it. Exits 1 if any unwaived 'block' rule fails — usable as a CI gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from design_os.lint.engine import blocking_failures, load_bindings, run_lint
from design_os.lint.extract import extract_style_snapshot, write_snapshot
from design_os.rules.loader import DEFAULT_CATALOG_PATH, applicable_rules, load_catalog, load_waivers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL to lint (or a path to an existing style-snapshot JSON)")
    parser.add_argument("--target-id", default="adhoc", help="Target id used for waiver scoping")
    parser.add_argument("--waivers", default="waivers.yaml")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH))
    parser.add_argument("--snapshot-out", default=None, help="Also write the extracted snapshot here")
    parser.add_argument("--artifact-type", default="page", help="Scope filter for applies_to (page, dashboard, chart, ...)")
    args = parser.parse_args()

    rules = applicable_rules(load_catalog(Path(args.catalog)), args.artifact_type)
    bindings = load_bindings()
    waivers_path = Path(args.waivers)
    waivers = (
        load_waivers(waivers_path, {r.id for r in rules}, today=date.today())
        if waivers_path.exists()
        else []
    )

    if Path(args.url).exists():
        snapshot = json.loads(Path(args.url).read_text(encoding="utf-8"))
    else:
        snapshot = extract_style_snapshot(args.url)
        if args.snapshot_out:
            write_snapshot(snapshot, Path(args.snapshot_out))

    verdicts = run_lint(snapshot, rules, bindings, target_id=args.target_id, waivers=waivers)
    order = {"fail": 0, "waived": 1, "unimplemented": 2, "n/a": 3, "pass": 4}
    for v in sorted(verdicts, key=lambda v: (order.get(v.status, 5), v.rule_id)):
        print(f"{v.status.upper():>13}  {v.rule_id}  [{v.severity}]  {v.evidence}")

    blockers = blocking_failures(verdicts)
    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v.status] = counts.get(v.status, 0) + 1
    print(f"\n{len(verdicts)} rules: " + ", ".join(f"{k}={n}" for k, n in sorted(counts.items())))
    if blockers:
        print(f"BLOCKED: {len(blockers)} unwaived block failure(s) — fix or waive before shipping.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
