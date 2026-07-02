"""Real (non-mocked) wiring for run_target: audit-only for v1.

Live wiring covers rendering a real screenshot, running a real critique against
the kai-taste rubric, and gating/recording the result — but not auto-repair.
Auto-repair (write a CSS override, re-render, re-critique) only makes sense for
an artifact design-os can rewrite and re-render; a watchlist URL is something
design-os can only observe. apply_deterministic_fix is therefore a no-op here,
and callers should pass max_iterations=1 to run_target for url-based targets
so the loop doesn't burn real render/critique calls it can't act on.
"""
from pathlib import Path
import yaml

from design_os.critique.runner import run_qa, run_vision_critique, parse_vision_manifest
from design_os.critique.rubric_prompt import build_rubric_prompt
from design_os.dashboard.build import record_run
from design_os.gate import submit, finalize
from design_os.orchestrator.run import RunDeps, run_target
from design_os.orchestrator.signals import Target


def build_audit_spec(work_dir: Path) -> Path:
    """Write a minimal one-entry docs-spec.yaml auditing just the homepage route.

    qa.py requires a --spec file listing routes; a bare watchlist URL target has
    no route list of its own, so this is the smallest valid spec that satisfies it.
    """
    spec_path = Path(work_dir) / "audit-spec.yaml"
    spec_path.write_text(
        yaml.safe_dump({"entries": [{"id": "home", "route": "/"}]}, sort_keys=False),
        encoding="utf-8",
    )
    return spec_path


def write_rubric_prompt_file(work_dir: Path) -> Path:
    """Write the composed kai-taste rubric prompt to a file vision.py's --prompt-file can read."""
    prompt_path = Path(work_dir) / "rubric-prompt.txt"
    prompt_path.write_text(build_rubric_prompt(), encoding="utf-8")
    return prompt_path


def gate_for(target: Target) -> str:
    """Every real run today is 'safe': design-os has no publish/deploy driver, so nothing
    it does actually changes a live surface yet — there is no 'irreversible' action to gate.
    """
    return "safe"


def _no_op_apply_deterministic_fix(finding: dict, overrides_path: Path) -> bool:
    """Audit-only: report findings, never attempt to auto-fix a target design-os can't rewrite."""
    return False


def build_live_deps(work_root: Path, store, run_date: str, pass_threshold: int = 25) -> RunDeps:
    """Construct a RunDeps wired to the real render/critique/gate pipeline.

    work_root is a per-invocation scratch directory (screenshots, manifests, the
    audit spec and rubric prompt files, and the CSS-overrides dir run_target always
    computes a path under even though apply_deterministic_fix never writes to it).
    """
    work_root = Path(work_root)
    overrides_dir = work_root / "overrides"
    overrides_dir.mkdir(parents=True, exist_ok=True)
    spec_path = build_audit_spec(work_root)
    prompt_path = write_rubric_prompt_file(work_root)

    def render(target: Target) -> Path:
        env_file = work_root / f"{target.id}.env"
        if not env_file.exists():
            env_file.write_text("", encoding="utf-8")
        run_root = work_root / "runs" / target.id
        return run_qa(env_file, run_root, base_url=target.url, spec=spec_path)

    def critique(run_dir: Path):
        # run_qa is invoked with a fixed --spec; run_vision_critique doesn't take one,
        # so point it at the same audit-spec-driven run_dir qa.py just wrote to.
        manifest_path = run_vision_critique(run_dir, prompt_path)
        return parse_vision_manifest(manifest_path)

    def submit_item(item: dict) -> str:
        return submit(store, item)

    def finalize_item(item_id: str) -> None:
        finalize(store, item_id)

    return RunDeps(
        render=render,
        critique=critique,
        apply_deterministic_fix=_no_op_apply_deterministic_fix,
        overrides_dir=overrides_dir,
        submit_item=submit_item,
        finalize_item=finalize_item,
        gate_for=gate_for,
        run_date=run_date,
        pass_threshold=pass_threshold,
    )


def run_watchlist_live(
    due: list[Target], deps: RunDeps, dashboard_db_path: Path, run_target_fn=run_target
) -> list[dict]:
    """Run each due url target through run_target_fn (real audit, one iteration), recording
    every result to the dashboard. watch_dir targets are skipped: there is no render hook for
    an arbitrary local directory yet (a factory-output re-render integration is a separate,
    not-yet-designed piece — see docs/superpowers/specs/2026-07-02-design-os-design.md).
    """
    results = []
    for target in due:
        if target.watch_dir:
            print(f"SKIP: {target.id} (watch_dir targets have no live render hook yet)")
            continue
        result = run_target_fn(target, deps, max_iterations=1)
        record_run(dashboard_db_path, result)
        print(f"AUDITED: {target.id} score={result['final_score']}/30 gate={result['gate']}")
        results.append(result)
    return results
