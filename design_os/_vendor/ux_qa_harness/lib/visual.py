"""Visual baseline comparison helpers."""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageChops


def compare_or_update(
    screenshot: Path,
    *,
    entry_id: str,
    baseline_dir: Path,
    run_dir: Path,
    update: bool = False,
    threshold: float = 0.01,
) -> dict:
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline = baseline_dir / f"{entry_id}.png"

    if update or not baseline.exists():
        shutil.copy2(screenshot, baseline)
        return {
            "status": "updated" if update else "baseline_created",
            "baseline": str(baseline),
            "mismatch_ratio": 0.0,
            "threshold": threshold,
        }

    try:
        with Image.open(screenshot).convert("RGBA") as current, Image.open(baseline).convert("RGBA") as expected:
            if current.size != expected.size:
                return {
                    "status": "changed",
                    "baseline": str(baseline),
                    "mismatch_ratio": 1.0,
                    "threshold": threshold,
                    "reason": f"size changed from {expected.size[0]}x{expected.size[1]} to {current.size[0]}x{current.size[1]}",
                }
            diff = ImageChops.difference(current, expected)
            alpha = diff.convert("L").point(lambda px: 255 if px > 16 else 0)
            changed = sum(1 for px in alpha.getdata() if px)
            total = current.size[0] * current.size[1]
            ratio = changed / total if total else 0
            status = "changed" if ratio > threshold else "unchanged"
            out: dict = {
                "status": status,
                "baseline": str(baseline),
                "mismatch_ratio": ratio,
                "threshold": threshold,
                "changed_pixels": changed,
                "total_pixels": total,
            }
            if status == "changed":
                diff_dir = run_dir / "visual-diffs"
                diff_dir.mkdir(exist_ok=True)
                diff_path = diff_dir / f"{entry_id}.png"
                diff.save(diff_path)
                out["diff"] = str(diff_path.relative_to(run_dir))
            return out
    except Exception as exc:
        return {
            "status": "error",
            "baseline": str(baseline),
            "threshold": threshold,
            "error": f"{type(exc).__name__}: {exc}",
        }
