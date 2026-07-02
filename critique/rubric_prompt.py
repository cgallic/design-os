"""Compose the kai-taste rubric into a vision.py-compatible critique prompt."""
from pathlib import Path

JSON_CONTRACT = """
Respond with minified JSON matching this exact shape:
{
  "issues": [
    {"heuristic": "<pillar or failure-mode name>", "description": "...", "evidence": "...", "severity": 0-4, "confidence": 0.0-1.0, "fix": "..."}
  ],
  "working_well": ["..."],
  "scorecard": {
    "pillars": {"deterministic_stochastic_balance": 1-10, "interaction_density": 1-10, "visual_cohesion": 1-10},
    "composite": 3-30,
    "failure_modes_present": ["..."],
    "prioritized_fixes": [{"priority": "P0|P1|P2", "fix": "...", "pillar": "..."}]
  }
}
""".strip()


def build_rubric_prompt(skill_md_path: Path, pillar_rubrics_path: Path) -> str:
    """Read kai-taste's SKILL.md and pillar-rubrics.md and compose a critique prompt.

    Raises FileNotFoundError if either source file is missing.
    """
    skill_md_path = Path(skill_md_path)
    pillar_rubrics_path = Path(pillar_rubrics_path)
    skill_text = skill_md_path.read_text(encoding="utf-8")
    pillar_text = pillar_rubrics_path.read_text(encoding="utf-8")
    return (
        "You are auditing a rendered screenshot against the kai-taste design framework.\n\n"
        f"{skill_text}\n\n{pillar_text}\n\n{JSON_CONTRACT}"
    )
