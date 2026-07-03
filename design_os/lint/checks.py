"""Pure deterministic checks over a style snapshot.

Every function here takes the style snapshot (a plain dict — see
design_os/lint/extract.py for the schema and the only place it is produced)
plus keyword params supplied by the rule binding, and returns
(status, evidence) where status is "pass" | "fail" | "n/a".

These are the teeth of the harness: rules with numbers get computed here,
not narrated by a vision model. Keep every function pure — no I/O, no globals —
so a fixture snapshot exercises them completely in tests.
"""
from __future__ import annotations

import re

# --- color helpers ---------------------------------------------------------

_RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")


def parse_color(value: str) -> tuple[int, int, int, float] | None:
    """Parse '#rrggbb', '#rgb', 'rgb(...)', 'rgba(...)' into (r, g, b, alpha). None if unparseable."""
    value = (value or "").strip()
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        if len(raw) != 6:
            return None
        try:
            return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), 1.0
        except ValueError:
            return None
    match = _RGB_RE.match(value)
    if match:
        r, g, b = int(match[1]), int(match[2]), int(match[3])
        alpha = float(match[4]) if match[4] is not None else 1.0
        return r, g, b, alpha
    return None


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1, l2 = _relative_luminance(fg), _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# --- checks ----------------------------------------------------------------


def check_contrast_min(snapshot: dict, ratio_normal: float = 4.5, ratio_large: float = 3.0) -> tuple[str, str]:
    """WCAG 1.4.3: text contrast >= ratio_normal (>= ratio_large for large text)."""
    failures = []
    checked = 0
    for style in snapshot.get("text_styles", []):
        fg = parse_color(style.get("color", ""))
        bg = parse_color(style.get("background_color", ""))
        if fg is None or bg is None or fg[3] < 1.0 or bg[3] < 1.0:
            continue  # translucent or unparseable: composite unknown, don't guess
        checked += 1
        required = ratio_large if style.get("is_large_text") else ratio_normal
        ratio = contrast_ratio(fg[:3], bg[:3])
        if ratio < required:
            failures.append(f"{style.get('selector', '?')}: {ratio:.2f} < {required}")
    if checked == 0:
        return "n/a", "no opaque text/background pairs measurable"
    if failures:
        return "fail", f"{len(failures)}/{checked} text styles below ratio: " + "; ".join(failures[:5])
    return "pass", f"all {checked} measurable text styles pass"


def check_font_family_max(snapshot: dict, max_families: int = 2, ignore_monospace: bool = True) -> tuple[str, str]:
    families = set()
    for stack in snapshot.get("font_families", []):
        primary = stack.split(",")[0].strip().strip("'\"").lower()
        if not primary:
            continue
        if ignore_monospace and ("mono" in stack.lower() or primary in ("courier", "courier new", "consolas", "menlo")):
            continue
        families.add(primary)
    if not families:
        return "n/a", "no font families observed"
    if len(families) > max_families:
        return "fail", f"{len(families)} families in use (max {max_families}): {sorted(families)}"
    return "pass", f"{len(families)} families: {sorted(families)}"


def check_type_scale_size_count(snapshot: dict, max_sizes: int = 8, tolerance_px: float = 0.5) -> tuple[str, str]:
    """A constrained type scale: no more than max_sizes distinct font sizes on a page."""
    sizes = sorted(set(round(s / tolerance_px) * tolerance_px for s in snapshot.get("font_sizes_px", [])))
    if not sizes:
        return "n/a", "no font sizes observed"
    if len(sizes) > max_sizes:
        return "fail", f"{len(sizes)} distinct font sizes (max {max_sizes}): {sizes}"
    return "pass", f"{len(sizes)} distinct font sizes: {sizes}"


def check_body_font_min(snapshot: dict, min_px: float = 16.0, sample_threshold: int = 50) -> tuple[str, str]:
    """Body text (long-form runs) must be at least min_px."""
    bodies = [
        s for s in snapshot.get("text_styles", []) if len(s.get("sample_text", "") or "") >= sample_threshold
    ]
    if not bodies:
        return "n/a", "no body-length text runs observed"
    failures = [f"{s.get('selector', '?')}: {s['font_size_px']}px" for s in bodies if s["font_size_px"] < min_px]
    if failures:
        return "fail", f"body text below {min_px}px: " + "; ".join(failures[:5])
    return "pass", f"all {len(bodies)} body runs >= {min_px}px"


def check_min_font_size(snapshot: dict, min_px: float = 11.0) -> tuple[str, str]:
    """Nothing on screen below the legibility floor, anywhere."""
    sizes = snapshot.get("font_sizes_px", [])
    if not sizes:
        return "n/a", "no font sizes observed"
    below = sorted(s for s in sizes if s < min_px)
    if below:
        return "fail", f"font sizes below {min_px}px floor: {below}"
    return "pass", f"smallest size {min(sizes)}px >= {min_px}px"


def check_line_height_range(
    snapshot: dict, min_ratio: float = 1.2, max_ratio: float = 1.55, sample_threshold: int = 50
) -> tuple[str, str]:
    """Body text line height within [min_ratio, max_ratio] x font size (Butterick: 120-145%)."""
    failures = []
    checked = 0
    for style in snapshot.get("text_styles", []):
        if len(style.get("sample_text", "") or "") < sample_threshold:
            continue
        size, height = style.get("font_size_px"), style.get("line_height_px")
        if not size or not height:
            continue
        checked += 1
        ratio = height / size
        if not (min_ratio <= ratio <= max_ratio):
            failures.append(f"{style.get('selector', '?')}: {ratio:.2f}")
    if checked == 0:
        return "n/a", "no measurable body text"
    if failures:
        return "fail", f"line-height ratio outside [{min_ratio}, {max_ratio}]: " + "; ".join(failures[:5])
    return "pass", f"all {checked} body runs within [{min_ratio}, {max_ratio}]"


def check_line_length(
    snapshot: dict, min_chars: int = 45, max_chars: int = 90, sample_threshold: int = 120
) -> tuple[str, str]:
    """Long-form measure of 45-90 characters per line."""
    failures = []
    checked = 0
    for style in snapshot.get("text_styles", []):
        chars = style.get("chars_per_line")
        if chars is None or len(style.get("sample_text", "") or "") < sample_threshold:
            continue
        checked += 1
        if not (min_chars <= chars <= max_chars):
            failures.append(f"{style.get('selector', '?')}: {chars} chars/line")
    if checked == 0:
        return "n/a", "no long-form text blocks measurable"
    if failures:
        return "fail", f"measure outside {min_chars}-{max_chars} chars: " + "; ".join(failures[:5])
    return "pass", f"all {checked} long-form blocks within {min_chars}-{max_chars} chars"


def check_spacing_grid(snapshot: dict, grid_px: int = 4, min_conformance: float = 0.8) -> tuple[str, str]:
    """At least min_conformance of observed spacing values sit on the grid_px grid."""
    spacings = [s for s in snapshot.get("spacings_px", []) if s > 0]
    if not spacings:
        return "n/a", "no spacing values observed"
    on_grid = sum(1 for s in spacings if abs(s - round(s / grid_px) * grid_px) < 0.5)
    conformance = on_grid / len(spacings)
    off = sorted({round(s, 1) for s in spacings if abs(s - round(s / grid_px) * grid_px) >= 0.5})
    if conformance < min_conformance:
        return "fail", f"{conformance:.0%} of spacings on {grid_px}px grid (need {min_conformance:.0%}); off-grid: {off[:10]}"
    return "pass", f"{conformance:.0%} of {len(spacings)} spacings on {grid_px}px grid"


def check_tap_target_min(snapshot: dict, min_px: float = 24.0) -> tuple[str, str]:
    """Interactive targets at least min_px in both dimensions (WCAG 2.2 AA: 24px)."""
    targets = snapshot.get("interactive_targets", [])
    if not targets:
        return "n/a", "no interactive targets observed"
    failures = [
        f"{t.get('selector', '?')}: {t['width']:.0f}x{t['height']:.0f}"
        for t in targets
        if t["width"] < min_px or t["height"] < min_px
    ]
    if failures:
        return "fail", f"targets below {min_px}px: " + "; ".join(failures[:5])
    return "pass", f"all {len(targets)} targets >= {min_px}px"


def check_heading_hierarchy(snapshot: dict) -> tuple[str, str]:
    """Exactly one h1; no skipped heading levels."""
    headings = snapshot.get("headings", [])
    if not headings:
        return "n/a", "no headings observed"
    levels = [h["level"] for h in headings]
    problems = []
    if levels.count(1) != 1:
        problems.append(f"{levels.count(1)} h1 elements (need exactly 1)")
    seen = {1} if 1 in levels else set()
    for level in levels:
        if level > 1 and (level - 1) not in seen and level not in seen:
            problems.append(f"h{level} appears without h{level - 1}")
        seen.add(level)
    if problems:
        return "fail", "; ".join(sorted(set(problems)))
    return "pass", f"{len(headings)} headings, single h1, no skipped levels"


def check_color_budget(snapshot: dict, max_saturated_hues: int = 3, hue_bucket_deg: int = 30) -> tuple[str, str]:
    """A palette has intent: at most max_saturated_hues distinct saturated hue families."""
    hues = set()
    for value in snapshot.get("colors", {}).get("all", []):
        parsed = parse_color(value)
        if parsed is None:
            continue
        r, g, b, _ = parsed
        mx, mn = max(r, g, b), min(r, g, b)
        if mx == 0 or (mx - mn) / mx < 0.25 or mx < 40:
            continue  # grays / near-blacks don't spend the hue budget
        if mx == mn:
            continue
        if mx == r:
            hue = (60 * ((g - b) / (mx - mn))) % 360
        elif mx == g:
            hue = 60 * ((b - r) / (mx - mn)) + 120
        else:
            hue = 60 * ((r - g) / (mx - mn)) + 240
        hues.add(int(hue // hue_bucket_deg))
    if not hues:
        return "n/a", "no saturated colors observed"
    if len(hues) > max_saturated_hues:
        return "fail", f"{len(hues)} saturated hue families (max {max_saturated_hues})"
    return "pass", f"{len(hues)} saturated hue families"


def check_alt_text(snapshot: dict) -> tuple[str, str]:
    missing = snapshot.get("images_missing_alt")
    if missing is None:
        return "n/a", "alt-text data not collected"
    if missing > 0:
        return "fail", f"{missing} content images missing alt text"
    return "pass", "all content images carry alt text"


def check_animation_duration(snapshot: dict, min_ms: float = 100.0, max_ms: float = 500.0) -> tuple[str, str]:
    """UI transitions within the perceptible-but-not-sluggish band."""
    animations = snapshot.get("animations", [])
    if not animations:
        return "n/a", "no animations observed"
    failures = [
        f"{a.get('selector', '?')}: {a['duration_ms']:.0f}ms"
        for a in animations
        if a.get("duration_ms") and not (min_ms <= a["duration_ms"] <= max_ms)
    ]
    if failures:
        return "fail", f"durations outside {min_ms:.0f}-{max_ms:.0f}ms: " + "; ".join(failures[:5])
    return "pass", f"all {len(animations)} animation durations within {min_ms:.0f}-{max_ms:.0f}ms"


# Registry consumed by the engine; bindings.yaml refers to checks by these names.
CHECKS = {
    "contrast_min": check_contrast_min,
    "font_family_max": check_font_family_max,
    "type_scale_size_count": check_type_scale_size_count,
    "body_font_min": check_body_font_min,
    "min_font_size": check_min_font_size,
    "line_height_range": check_line_height_range,
    "line_length": check_line_length,
    "spacing_grid": check_spacing_grid,
    "tap_target_min": check_tap_target_min,
    "heading_hierarchy": check_heading_hierarchy,
    "color_budget": check_color_budget,
    "alt_text": check_alt_text,
    "animation_duration": check_animation_duration,
}
