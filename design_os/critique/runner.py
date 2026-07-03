"""Wrap the vendored ux-qa-harness qa.py and vision.py as subprocesses; parse their output."""
from dataclasses import dataclass, field
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
    # Merged harness verdicts (design_os.lint.engine.Verdict) from the lint pass and the
    # lens panel; empty when the run predates the harness or the catalog is absent.
    verdicts: list = field(default_factory=list)


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


def parse_lens_verdicts(manifest_path: Path) -> list[dict]:
    """Collect raw per-rule verdict dicts from a lens pass's vision-manifest.json,
    across all routes. Entries without verdicts (model error, old prompt) contribute
    nothing rather than crashing the panel."""
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    verdicts: list[dict] = []
    for entry in data.get("results", []):
        verdicts.extend(entry.get("verdicts") or [])
    return verdicts


def run_qa(env_file: Path, run_root: Path, base_url: str | None = None, spec: Path | None = None) -> Path:
    """Run ux-qa-harness's qa.py against env_file; return the created run directory.

    run_root is passed as UXQA_RUNTIME_ROOT so output lands under our control.
    base_url, if given, overrides UXQA_BASE_URL via qa.py's own --base-url flag,
    so a target's URL can be audited without needing a real env file to exist.
    spec, if given, overrides qa.py's default --spec (docs-spec.yaml, which isn't
    vendored) with a caller-supplied route list.
    """
    cmd = [
        sys.executable,
        str(UX_QA_HARNESS_DIR / "qa.py"),
        "--env-file",
        str(env_file),
    ]
    if base_url:
        cmd += ["--base-url", base_url]
    if spec:
        cmd += ["--spec", str(spec)]
    env = {**os.environ, "UXQA_RUNTIME_ROOT": str(run_root)}
    # No check=True: qa.py exits 1 by design when it finds a critical-severity route (its own
    # CI-style signal, not a crash) while still writing a real manifest. A genuine subprocess
    # failure (crash, no manifest at all) is caught below by the empty-glob check instead.
    subprocess.run(cmd, cwd=str(UX_QA_HARNESS_DIR), env=env)
    runs_dir = Path(run_root) / "runs"
    matches = sorted(runs_dir.glob("*-qa"))
    if not matches:
        raise RuntimeError(
            f"qa.py produced no *-qa run directory under {runs_dir} (crashed before writing output?)"
        )
    run_dir = matches[-1]
    if not (run_dir / "qa-manifest.json").exists():
        # A *-qa dir can exist with no manifest if qa.py crashed mid-run, or if this lookup
        # landed on a stale dir from an earlier invocation reusing the same run_root.
        raise RuntimeError(f"qa.py produced no qa-manifest.json in {run_dir} (crashed mid-run?)")
    return run_dir


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
