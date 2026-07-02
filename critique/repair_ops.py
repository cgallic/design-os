"""Classify kai-taste findings and compute deterministic fixes."""
from dataclasses import dataclass
from pathlib import Path
import re

_PATTERNS: list[tuple[str, str]] = [
    (r"contrast", "contrast"),
    (r"touch target", "touch_target"),
    (r"off-grid spacing|spacing.*grid|grid.*spacing", "spacing"),
    (r"affordance collapse|doesn't look (clickable|interactive)", "affordance"),
    (r"cohesion rigidity|off-token|not a design token", "token_snap"),
]


def classify_finding(finding: dict) -> str:
    """Return a fix-type string, or "flag" if this requires human judgment."""
    haystack = f"{finding.get('heuristic', '')} {finding.get('description', '')}".lower()
    for pattern, fix_type in _PATTERNS:
        if re.search(pattern, haystack):
            return fix_type
    return "flag"


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = channel(r), channel(g), channel(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    l1, l2 = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def fix_contrast(fg_hex: str, bg_hex: str, target_ratio: float = 4.5) -> str:
    """Darken (or lighten) fg_hex in fixed steps until it passes target_ratio against bg_hex."""
    if _contrast_ratio(fg_hex, bg_hex) >= target_ratio:
        return fg_hex
    r, g, b = (int(fg_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    bg_is_light = _relative_luminance(bg_hex) > 0.5
    step = -8 if bg_is_light else 8
    for _ in range(32):
        r = max(0, min(255, r + step))
        g = max(0, min(255, g + step))
        b = max(0, min(255, b + step))
        candidate = f"#{r:02x}{g:02x}{b:02x}"
        if _contrast_ratio(candidate, bg_hex) >= target_ratio:
            return candidate
        if r in (0, 255) and g in (0, 255) and b in (0, 255):
            break
    return candidate


def snap_to_grid(value_px: float, grid: int = 8) -> int:
    """Round value_px to the nearest multiple of grid."""
    return round(value_px / grid) * grid


def nearest_token(value: float, tokens: list[float]) -> float:
    """Return the token in tokens closest to value."""
    return min(tokens, key=lambda t: abs(t - value))


@dataclass
class RepairResult:
    finding_id: str
    fix_type: str
    css_variable: str
    new_value: str


def apply_repair(result: RepairResult, overrides_path: Path) -> None:
    """Write (or append) a :root CSS custom-property override for this repair."""
    overrides_path = Path(overrides_path)
    line = f"  {result.css_variable}: {result.new_value};"
    if overrides_path.exists():
        content = overrides_path.read_text(encoding="utf-8")
        # Insert before the closing brace of the existing :root block.
        assert content.rstrip().endswith("}"), "overrides.css must end with a closing brace"
        content = content.rstrip()[:-1].rstrip() + f"\n{line}\n}}\n"
    else:
        content = f":root {{\n{line}\n}}\n"
    overrides_path.write_text(content, encoding="utf-8")
