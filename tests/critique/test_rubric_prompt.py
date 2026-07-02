from pathlib import Path
from critique.rubric_prompt import build_rubric_prompt

FIXTURES = Path(__file__).parent.parent / "fixtures" / "kai-taste"


def test_build_rubric_prompt_includes_pillar_and_rubric_content():
    prompt = build_rubric_prompt(FIXTURES / "SKILL.md", FIXTURES / "pillar-rubrics.md")
    assert "Three Pillars" in prompt
    assert "Affordance Collapse" in prompt
    assert "Visual Cohesion, 1-10 criteria" in prompt


def test_build_rubric_prompt_specifies_json_contract():
    prompt = build_rubric_prompt(FIXTURES / "SKILL.md", FIXTURES / "pillar-rubrics.md")
    assert '"issues"' in prompt
    assert '"scorecard"' in prompt
    assert '"working_well"' in prompt


def test_build_rubric_prompt_raises_on_missing_file(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        build_rubric_prompt(tmp_path / "missing.md", FIXTURES / "pillar-rubrics.md")
