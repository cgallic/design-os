import json
import subprocess
from pathlib import Path
from critique.runner import run_qa, run_vision_critique, parse_vision_manifest, CritiqueResult

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_vision_manifest_builds_critique_result():
    result = parse_vision_manifest(FIXTURES / "vision-manifest.json")
    assert isinstance(result, CritiqueResult)
    assert result.composite_score == 19
    assert len(result.issues) == 2
    assert len(result.prioritized_fixes) == 2
    assert result.prioritized_fixes[0]["priority"] == "P0"


def test_run_qa_invokes_subprocess_with_expected_args(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    env_file = tmp_path / "site.env"
    env_file.write_text("UXQA_BASE_URL=https://example.com\n", encoding="utf-8")
    run_root = tmp_path / "runtime"
    # fake subprocess.run doesn't create real files, so pre-create a run dir
    # for run_qa's sorted(runs_dir.glob("*-qa"))[-1] lookup to find.
    (run_root / "runs" / "2026-run-qa").mkdir(parents=True)

    run_qa(env_file, run_root)

    assert len(calls) == 1
    cmd = calls[0]
    assert "qa.py" in cmd[1] or "qa.py" in " ".join(cmd)
    assert "--env-file" in cmd
    assert str(env_file) in cmd


def test_run_vision_critique_invokes_subprocess_with_prompt_file(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_dir = tmp_path / "runs" / "2026-run-qa"
    run_dir.mkdir(parents=True)
    prompt_file = tmp_path / "rubric.txt"
    prompt_file.write_text("RUBRIC", encoding="utf-8")

    manifest_path = run_vision_critique(run_dir, prompt_file)

    assert manifest_path == run_dir / "vision-manifest.json"
    cmd = calls[0]
    assert "--prompt-file" in cmd
    assert str(prompt_file) in cmd
    assert "--run-dir" in cmd
    assert str(run_dir) in cmd
