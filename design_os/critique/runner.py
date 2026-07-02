"""Wrap the vendored ux-qa-harness qa.py and vision.py as subprocesses; parse their output."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import subprocess
import sys

UX_QA_HARNESS_DIR = Path(__file__).parent.parent / "_vendor" / "ux_qa_harness"


@dataclass
class CritiqueResult:
    composite_score: int
    issues: list[dict]
    prioritized_fixes: list[dict]
    pillars: dict


def parse_vision_manifest(manifest_path: Path) -> CritiqueResult:
    """Parse a vision-manifest.json (Task 3's rubric-prompt JSON contract) into a CritiqueResult.

    Aggregates across all routes in the manifest's "results" list.
    """
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    issues: list[dict] = []
    fixes: list[dict] = []
    composite_total = 0
    pillars: dict = {}
    for entry in data["results"]:
        issues.extend(entry["issues"])
        scorecard = entry["scorecard"]
        fixes.extend(scorecard["prioritized_fixes"])
        composite_total += scorecard["composite"]
        pillars = scorecard["pillars"]  # last route's pillar scores, for single-route runs this is the only one
    return CritiqueResult(
        composite_score=composite_total,
        issues=issues,
        prioritized_fixes=fixes,
        pillars=pillars,
    )


def run_qa(env_file: Path, run_root: Path) -> Path:
    """Run ux-qa-harness's qa.py against env_file; return the created run directory.

    run_root is passed as UXQA_RUNTIME_ROOT so output lands under our control.
    """
    cmd = [
        sys.executable,
        str(UX_QA_HARNESS_DIR / "qa.py"),
        "--env-file",
        str(env_file),
    ]
    env = {**os.environ, "UXQA_RUNTIME_ROOT": str(run_root)}
    subprocess.run(cmd, cwd=str(UX_QA_HARNESS_DIR), env=env, check=True)
    runs_dir = Path(run_root) / "runs"
    matches = sorted(runs_dir.glob("*-qa"))
    if not matches:
        raise RuntimeError(
            f"qa.py exited successfully but produced no *-qa run directory under {runs_dir}"
        )
    return matches[-1]


def run_vision_critique(run_dir: Path, prompt_file: Path) -> Path:
    """Run ux-qa-harness's vision.py against an existing run dir's screenshots; return the manifest path."""
    cmd = [
        sys.executable,
        str(UX_QA_HARNESS_DIR / "vision.py"),
        "--run-dir",
        str(run_dir),
        "--prompt-file",
        str(prompt_file),
    ]
    subprocess.run(cmd, cwd=str(UX_QA_HARNESS_DIR), check=True)
    return Path(run_dir) / "vision-manifest.json"
