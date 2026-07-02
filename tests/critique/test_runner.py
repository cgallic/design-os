import json
import subprocess
from pathlib import Path

import pytest

from design_os.critique.runner import run_qa, run_vision_critique, parse_vision_manifest, CritiqueResult

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


def test_run_qa_passes_base_url_override_when_given(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    env_file = tmp_path / "site.env"
    env_file.write_text("", encoding="utf-8")
    run_root = tmp_path / "runtime"
    (run_root / "runs" / "2026-run-qa").mkdir(parents=True)

    run_qa(env_file, run_root, base_url="https://kaicalls.com")

    cmd = calls[0]
    assert "--base-url" in cmd
    assert "https://kaicalls.com" in cmd


def test_run_qa_passes_spec_override_when_given(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    env_file = tmp_path / "site.env"
    env_file.write_text("", encoding="utf-8")
    run_root = tmp_path / "runtime"
    (run_root / "runs" / "2026-run-qa").mkdir(parents=True)
    spec_path = tmp_path / "audit-spec.yaml"

    run_qa(env_file, run_root, spec=spec_path)

    cmd = calls[0]
    assert "--spec" in cmd
    assert str(spec_path) in cmd


def test_run_qa_omits_base_url_flag_when_not_given(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    env_file = tmp_path / "site.env"
    env_file.write_text("UXQA_BASE_URL=https://example.com\n", encoding="utf-8")
    run_root = tmp_path / "runtime"
    (run_root / "runs" / "2026-run-qa").mkdir(parents=True)

    run_qa(env_file, run_root)

    cmd = calls[0]
    assert "--base-url" not in cmd


def test_run_qa_does_not_raise_when_qa_py_exits_1_but_produced_a_run_dir(monkeypatch, tmp_path):
    # qa.py's own CLI exits 1 when it finds a critical-severity route -- that's its normal
    # "here's the report" exit code, not a crash. run_qa must not treat it as a subprocess
    # failure as long as a real *-qa run directory (with a manifest) was still produced.
    # Mirrors real subprocess.run(check=True)'s behavior: raise CalledProcessError on non-zero
    # exit, so this test actually distinguishes a fixed run_qa from an unfixed one.
    def fake_run(cmd, check=False, **kwargs):
        completed = subprocess.CompletedProcess(cmd, 1)
        if check:
            raise subprocess.CalledProcessError(1, cmd)
        return completed

    monkeypatch.setattr(subprocess, "run", fake_run)
    env_file = tmp_path / "site.env"
    env_file.write_text("", encoding="utf-8")
    run_root = tmp_path / "runtime"
    run_dir = run_root / "runs" / "20260702T000000Z-qa"
    run_dir.mkdir(parents=True)

    result = run_qa(env_file, run_root, base_url="https://example.com")

    assert result == run_dir


def test_run_qa_raises_runtime_error_when_no_run_dir_produced(monkeypatch, tmp_path):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    env_file = tmp_path / "site.env"
    env_file.write_text("UXQA_BASE_URL=https://example.com\n", encoding="utf-8")
    run_root = tmp_path / "runtime"
    # deliberately do NOT create any *-qa run dir under run_root/runs, to
    # simulate qa.py exiting 0 but producing a degenerate/partial run.

    with pytest.raises(RuntimeError) as exc_info:
        run_qa(env_file, run_root)

    assert str(run_root / "runs") in str(exc_info.value)


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
