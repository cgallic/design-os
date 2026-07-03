"""Validate a design process log: `python -m design_os.process <log.yaml> [--stages brief,divergence,...]`

Exits 1 if any required stage gate fails. The log shape is documented in
design_os/process/protocol.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from design_os.process.protocol import STAGES, validate_process_log


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", help="Path to the process log YAML")
    parser.add_argument(
        "--stages",
        default=",".join(STAGES),
        help=f"Comma-separated stages to require (default: all — {','.join(STAGES)})",
    )
    args = parser.parse_args()

    log = yaml.safe_load(Path(args.log).read_text(encoding="utf-8")) or {}
    required = tuple(s.strip() for s in args.stages.split(",") if s.strip())
    results = validate_process_log(log, required_stages=required)

    failed = False
    for result in results:
        mark = "ok" if result.ok else "FAIL"
        print(f"{mark:>4}  {result.stage}")
        for problem in result.problems:
            print(f"        - {problem}")
        failed = failed or not result.ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
