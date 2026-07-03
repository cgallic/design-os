from design_os.lint.checks import (
    check_alt_text,
    check_animation_duration,
    check_body_font_min,
    check_color_budget,
    check_contrast_min,
    check_font_family_max,
    check_heading_hierarchy,
    check_line_height_range,
    check_line_length,
    check_min_font_size,
    check_spacing_grid,
    check_tap_target_min,
    check_type_scale_size_count,
    contrast_ratio,
    parse_color,
)

BODY = "x" * 200  # long enough to count as body / long-form text


def _text(selector="p", color="rgb(51, 51, 51)", bg="rgb(255, 255, 255)", size=16.0,
          line_height=24.0, chars=70, sample=BODY, large=False):
    return {
        "selector": selector,
        "font_family": "Inter, sans-serif",
        "font_size_px": size,
        "font_weight": 400,
        "line_height_px": line_height,
        "color": color,
        "background_color": bg,
        "chars_per_line": chars,
        "is_large_text": large,
        "sample_text": sample,
    }


def test_parse_color_forms():
    assert parse_color("#ffffff") == (255, 255, 255, 1.0)
    assert parse_color("#abc") == (170, 187, 204, 1.0)
    assert parse_color("rgb(1, 2, 3)") == (1, 2, 3, 1.0)
    assert parse_color("rgba(1, 2, 3, 0.5)") == (1, 2, 3, 0.5)
    assert parse_color("hotpink") is None


def test_contrast_ratio_black_on_white_is_21():
    assert round(contrast_ratio((0, 0, 0), (255, 255, 255)), 0) == 21


def test_contrast_fail_and_pass():
    snap = {"text_styles": [_text(color="rgb(170, 170, 170)")]}  # #aaa on white ~ 2.3:1
    status, evidence = check_contrast_min(snap)
    assert status == "fail" and "p" in evidence
    snap = {"text_styles": [_text()]}  # #333 on white ~ 12.6:1
    assert check_contrast_min(snap)[0] == "pass"


def test_contrast_large_text_uses_lower_bar():
    # #949494 on white is ~3.5:1 — fails 4.5 normal, passes 3.0 large
    snap = {"text_styles": [_text(color="rgb(148, 148, 148)", large=True)]}
    assert check_contrast_min(snap)[0] == "pass"


def test_contrast_skips_translucent():
    snap = {"text_styles": [_text(color="rgba(170, 170, 170, 0.5)")]}
    assert check_contrast_min(snap)[0] == "n/a"


def test_font_family_max():
    snap = {"font_families": ["Inter, sans-serif", "'Playfair Display', serif", "Menlo, monospace"]}
    assert check_font_family_max(snap, max_families=2)[0] == "pass"  # monospace exempt
    snap["font_families"].append("Comic Sans MS, cursive")
    assert check_font_family_max(snap, max_families=2)[0] == "fail"


def test_type_scale_size_count():
    snap = {"font_sizes_px": [12, 14, 16, 20, 24, 32]}
    assert check_type_scale_size_count(snap, max_sizes=8)[0] == "pass"
    snap = {"font_sizes_px": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21]}
    assert check_type_scale_size_count(snap, max_sizes=8)[0] == "fail"


def test_body_font_min_and_floor():
    snap = {"text_styles": [_text(size=14.0)]}
    assert check_body_font_min(snap, min_px=16.0)[0] == "fail"
    assert check_min_font_size({"font_sizes_px": [10.0, 16.0]}, min_px=11.0)[0] == "fail"
    assert check_min_font_size({"font_sizes_px": [12.0, 16.0]}, min_px=11.0)[0] == "pass"


def test_line_height_range():
    assert check_line_height_range({"text_styles": [_text(line_height=24.0)]})[0] == "pass"  # 1.5
    assert check_line_height_range({"text_styles": [_text(line_height=17.0)]})[0] == "fail"  # 1.06


def test_line_length():
    assert check_line_length({"text_styles": [_text(chars=70)]})[0] == "pass"
    assert check_line_length({"text_styles": [_text(chars=130)]})[0] == "fail"
    # short UI strings don't count as long-form
    assert check_line_length({"text_styles": [_text(chars=130, sample="Save")]})[0] == "n/a"


def test_spacing_grid():
    snap = {"spacings_px": [4, 8, 8, 16, 24, 32]}
    assert check_spacing_grid(snap, grid_px=4)[0] == "pass"
    snap = {"spacings_px": [5, 7, 13, 9, 11, 4]}
    status, evidence = check_spacing_grid(snap, grid_px=4)
    assert status == "fail" and "off-grid" in evidence


def test_tap_target_min():
    snap = {"interactive_targets": [{"selector": "a.nav", "width": 48, "height": 20}]}
    assert check_tap_target_min(snap, min_px=24)[0] == "fail"
    snap = {"interactive_targets": [{"selector": "a.nav", "width": 48, "height": 44}]}
    assert check_tap_target_min(snap, min_px=24)[0] == "pass"


def test_heading_hierarchy():
    good = {"headings": [{"level": 1}, {"level": 2}, {"level": 3}, {"level": 2}]}
    assert check_heading_hierarchy(good)[0] == "pass"
    two_h1 = {"headings": [{"level": 1}, {"level": 1}]}
    assert check_heading_hierarchy(two_h1)[0] == "fail"
    skipped = {"headings": [{"level": 1}, {"level": 4}]}
    assert check_heading_hierarchy(skipped)[0] == "fail"


def test_color_budget():
    snap = {"colors": {"all": ["rgb(200, 30, 30)", "rgb(30, 30, 200)", "rgb(128, 128, 128)", "rgb(20, 20, 20)"]}}
    assert check_color_budget(snap, max_saturated_hues=3)[0] == "pass"  # grays/near-black free
    rainbow = {"colors": {"all": ["rgb(200,30,30)", "rgb(200,200,30)", "rgb(30,200,30)", "rgb(30,200,200)", "rgb(30,30,200)"]}}
    assert check_color_budget(rainbow, max_saturated_hues=3)[0] == "fail"


def test_alt_text():
    assert check_alt_text({"images_missing_alt": 0})[0] == "pass"
    assert check_alt_text({"images_missing_alt": 3})[0] == "fail"
    assert check_alt_text({})[0] == "n/a"


def test_animation_duration():
    snap = {"animations": [{"selector": ".modal", "duration_ms": 250, "timing_function": "ease", "property": "opacity"}]}
    assert check_animation_duration(snap)[0] == "pass"
    snap = {"animations": [{"selector": ".modal", "duration_ms": 1200, "timing_function": "ease", "property": "opacity"}]}
    assert check_animation_duration(snap)[0] == "fail"
