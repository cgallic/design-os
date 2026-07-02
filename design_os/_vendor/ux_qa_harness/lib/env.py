"""Environment/config loading for UX-QA Harness.

Config is intentionally small and file-based so one repo can QA many sites
without baking customer secrets or runtime paths into source control.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ENV_PATH = Path.home() / ".uxqa" / "default.env"


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        out[key.strip()] = value
    return out


def load(env_file: str | None = None) -> dict[str, str]:
    """Load config from --env-file, UXQA_ENV_FILE, ~/.uxqa/default.env, and os.environ."""
    path = Path(env_file or os.environ.get("UXQA_ENV_FILE") or DEFAULT_ENV_PATH).expanduser()
    cfg = _parse_env_file(path)
    for key, value in cfg.items():
        os.environ.setdefault(key, value)
    merged = dict(cfg)
    for key, value in os.environ.items():
        if key.startswith("UXQA_"):
            merged[key] = value
    merged.setdefault("UXQA_ENV_FILE", str(path))
    merged.setdefault("UXQA_AUTH_MODE", "public")
    merged.setdefault("UXQA_RUNTIME_ROOT", str(Path.home() / ".uxqa" / "runs"))
    merged.setdefault("UXQA_STORAGE_STATE", str(Path.home() / ".uxqa" / "storage-state.json"))
    merged.setdefault("UXQA_REPORT_NAME", "UX-QA")
    return merged


def require(cfg: dict[str, str], *keys: str) -> dict[str, str]:
    missing = [k for k in keys if not cfg.get(k)]
    if missing:
        env_path = cfg.get("UXQA_ENV_FILE", str(DEFAULT_ENV_PATH))
        raise SystemExit(f"missing required env keys in {env_path}: {missing}")
    return {k: cfg[k] for k in keys}
