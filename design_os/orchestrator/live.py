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
import shutil
import yaml

from design_os.critique.lenses import DEFAULT_LENSES, build_lens_prompt, merge_lens_verdicts
from design_os.critique.runner import (
    parse_lens_verdicts,
    parse_vision_manifest,
    run_qa,
    run_vision_critique,
)
from design_os.critique.rubric_prompt import build_rubric_prompt, SCREENSHOT_INSTRUCTION
from design_os.dashboard.build import record_run
from design_os.gate import submit, finalize
from design_os.lint.engine import load_bindings, run_lint
from design_os.lint.extract import extract_style_snapshot, write_snapshot
from design_os.orchestrator.run import RunDeps, run_target
from design_os.orchestrator.signals import Target
from design_os.rules.loader import (
    DEFAULT_CATALOG_PATH,
    applicable_rules,
    load_catalog,
    load_waivers,
)


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


def write_lens_prompt_files(work_dir: Path, rules) -> dict[str, Path]:
    """Write one prompt file per critique lens; lenses with no vision rules are skipped
    loudly rather than silently judging nothing."""
    paths: dict[str, Path] = {}
    for lens in DEFAULT_LENSES:
        try:
            prompt = build_lens_prompt(lens, rules, screenshot_instruction=SCREENSHOT_INSTRUCTION)
        except ValueError as exc:
            print(f"WARN: skipping lens {lens.key}: {exc}")
            continue
        path = Path(work_dir) / f"lens-{lens.key}-prompt.txt"
        path.write_text(prompt, encoding="utf-8")
        paths[lens.key] = path
    return paths


def build_live_deps(
    work_root: Path,
    store,
    run_date: str,
    pass_threshold: int = 25,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    waivers_path: Path | None = None,
    today=None,
) -> RunDeps:
    """Construct a RunDeps wired to the real render/critique/gate pipeline.

    work_root is a per-invocation scratch directory (screenshots, manifests, the
    audit spec and rubric prompt files, and the CSS-overrides dir run_target always
    computes a path under even though apply_deterministic_fix never writes to it).

    When the rule catalog exists, every critique additionally runs the harness:
    the three-lens critique panel (per-rule vision verdicts) and the deterministic
    lint pass over a live style snapshot. Verdicts land on CritiqueResult.verdicts,
    where run_target's block-gate picks them up.
    """
    from datetime import date

    work_root = Path(work_root)
    overrides_dir = work_root / "overrides"
    overrides_dir.mkdir(parents=True, exist_ok=True)
    spec_path = build_audit_spec(work_root)
    prompt_path = write_rubric_prompt_file(work_root)

    rules = []
    waivers = []
    lens_prompt_paths: dict[str, Path] = {}
    bindings = []
    catalog_path = Path(catalog_path)
    if catalog_path.exists():
        # Watchlist audits evaluate rendered pages; identity/print/org/project-scoped
        # rules (brand ceremony, grid-spec paperwork, team policy) must not fire here.
        rules = applicable_rules(load_catalog(catalog_path), "page")
        bindings = load_bindings()
        if waivers_path is not None:
            waivers = load_waivers(
                Path(waivers_path), {r.id for r in rules}, today=today or date.today()
            )
        lens_prompt_paths = write_lens_prompt_files(work_root, rules)
    else:
        print(f"WARN: no rule catalog at {catalog_path}; running legacy single-rubric critique only")

    # render() records the target it just rendered so critique(), whose signature is
    # fixed by RunDeps, knows which URL/id the harness passes belong to.
    current: dict = {}

    def render(target: Target) -> Path:
        env_file = work_root / f"{target.id}.env"
        if not env_file.exists():
            env_file.write_text("", encoding="utf-8")
        run_root = work_root / "runs" / target.id
        current["target"] = target
        return run_qa(env_file, run_root, base_url=target.url, spec=spec_path)

    def critique(run_dir: Path):
        # run_qa is invoked with a fixed --spec; run_vision_critique doesn't take one,
        # so point it at the same audit-spec-driven run_dir qa.py just wrote to.
        manifest_path = run_vision_critique(run_dir, prompt_path)
        result = parse_vision_manifest(manifest_path)
        if not rules:
            return result

        target: Target = current["target"]

        # Lens panel: one vision pass per lens; vision.py always writes
        # vision-manifest.json, so each pass's manifest is moved aside by lens key.
        per_lens: dict[str, list[dict]] = {}
        for lens_key, lens_prompt_path in lens_prompt_paths.items():
            try:
                lens_manifest = run_vision_critique(run_dir, lens_prompt_path)
                kept = Path(run_dir) / f"vision-manifest-{lens_key}.json"
                shutil.move(str(lens_manifest), str(kept))
                per_lens[lens_key] = parse_lens_verdicts(kept)
            except Exception as exc:  # a dead lens degrades the panel, not the run
                print(f"WARN: lens {lens_key} failed for {target.id}: {exc}")
        vision_verdicts = merge_lens_verdicts(per_lens, rules, target_id=target.id, waivers=waivers)

        # Deterministic lint over a live style snapshot.
        lint_verdicts = []
        if target.url:
            try:
                snapshot = extract_style_snapshot(target.url)
                write_snapshot(snapshot, Path(run_dir) / "style-snapshot.json")
                lint_verdicts = run_lint(snapshot, rules, bindings, target_id=target.id, waivers=waivers)
            except Exception as exc:
                print(f"WARN: style-snapshot lint failed for {target.id}: {exc}")

        result.verdicts = lint_verdicts + vision_verdicts
        return result

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
