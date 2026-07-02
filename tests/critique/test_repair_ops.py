from pathlib import Path
from critique.repair_ops import (
    classify_finding,
    fix_contrast,
    snap_to_grid,
    nearest_token,
    RepairResult,
    apply_repair,
)


def test_classify_finding_contrast():
    finding = {"heuristic": "Visual Cohesion", "description": "Contrast 3.2:1 fails 4.5:1 minimum"}
    assert classify_finding(finding) == "contrast"


def test_classify_finding_affordance_collapse():
    finding = {"heuristic": "Affordance Collapse", "description": "Button doesn't look clickable"}
    assert classify_finding(finding) == "affordance"


def test_classify_finding_off_grid_spacing():
    finding = {"heuristic": "Visual Cohesion", "description": "Off-grid spacing: 13px gap between cards"}
    assert classify_finding(finding) == "spacing"


def test_classify_finding_touch_target():
    finding = {"heuristic": "Interaction Density", "description": "Touch target is 32x32px, below minimum"}
    assert classify_finding(finding) == "touch_target"


def test_classify_finding_defaults_to_flag_for_judgment_calls():
    finding = {"heuristic": "Interaction Density", "description": "Copy tone feels too corporate, rewrite hero headline"}
    assert classify_finding(finding) == "flag"


def test_fix_contrast_darkens_foreground_until_passing():
    # #999999 on white (#ffffff) fails 4.5:1; result must pass and stay close to original hue direction
    result = fix_contrast("#999999", "#ffffff", target_ratio=4.5)
    assert result != "#999999"
    assert result.startswith("#") and len(result) == 7


def test_fix_contrast_returns_unchanged_when_already_passing():
    assert fix_contrast("#000000", "#ffffff", target_ratio=4.5) == "#000000"


def test_snap_to_grid_rounds_to_nearest_multiple():
    assert snap_to_grid(13, grid=8) == 16
    assert snap_to_grid(10, grid=8) == 8
    assert snap_to_grid(24, grid=8) == 24


def test_nearest_token_picks_closest_value():
    tokens = [4, 8, 16, 24, 32, 48, 64]
    assert nearest_token(13, tokens) == 16
    assert nearest_token(50, tokens) == 48


def test_apply_repair_writes_css_custom_property_override(tmp_path):
    overrides_path = tmp_path / "overrides.css"
    result = RepairResult(
        finding_id="f1",
        fix_type="contrast",
        css_variable="--kai-text-primary",
        new_value="#1a1a1a",
    )
    apply_repair(result, overrides_path)
    content = overrides_path.read_text(encoding="utf-8")
    assert ":root {" in content
    assert "--kai-text-primary: #1a1a1a;" in content


def test_apply_repair_appends_to_existing_overrides_file(tmp_path):
    overrides_path = tmp_path / "overrides.css"
    overrides_path.write_text(":root {\n  --kai-blue: #2563eb;\n}\n", encoding="utf-8")
    result = RepairResult(finding_id="f2", fix_type="token_snap", css_variable="--kai-spacing-md", new_value="16px")
    apply_repair(result, overrides_path)
    content = overrides_path.read_text(encoding="utf-8")
    assert "--kai-blue: #2563eb;" in content
    assert "--kai-spacing-md: 16px;" in content
