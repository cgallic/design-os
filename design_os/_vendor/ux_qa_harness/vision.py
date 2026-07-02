#!/usr/bin/env python3
"""Vision usability critique tier for UX-QA Harness.

Runs Claude (via the box's `claude -p`, no API key needed) over the per-route
screenshots qa.py ALREADY captured, and reports grounded, prioritized UX issues
with concrete fixes. No browser, no re-driving - pure judgment pass over the PNGs,
so it composes with qa.py as a cascade: cheap deterministic crawl first
(console/network/selector), then this vision critique on the same screenshots.

Anti-hallucination (the known VLM failure mode is inventing issues): every issue
must quote visible on-screen evidence, bucket into a Nielsen heuristic, and carry
a confidence; low-confidence issues are dropped and an empty list is allowed.

Usage:
  .venv/bin/python vision.py                        # latest -qa run's screenshots
  .venv/bin/python vision.py --run-dir <dir>
  .venv/bin/python vision.py --only connections --min-confidence 0.6
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

import os

RUNTIME_ROOT = Path(os.environ.get("UXQA_RUNTIME_ROOT", str(Path.home() / ".uxqa" / "runs"))).expanduser()
if RUNTIME_ROOT.name != "runs":
    RUNTIME_ROOT = RUNTIME_ROOT / "runs"
CLAUDE_TIMEOUT = 180  # seconds per screenshot (agentic Read + analysis)

DEFAULT_PROMPT = """You are a senior UX auditor reviewing ONE screenshot from a website or web app.
Route: <<ROUTE>>

First, use the Read tool to open the image at: <<PATH>>

Rules:
- Report ONLY issues you can directly SEE in this image. Every issue MUST quote the exact
  visible on-screen text and/or name the screen region (e.g. "top-right header").
- If you cannot ground an issue in visible evidence, do NOT report it.
- Bucket each issue into exactly one Nielsen heuristic (H1 visibility, H2 match real world,
  H3 user control, H4 consistency, H5 error prevention, H6 recognition, H7 flexibility,
  H8 minimalist design, H9 error recovery, H10 help/docs).
- It is correct to return an empty "issues" array if the screen looks fine.
- Do NOT speculate about behavior you cannot see (hover states, next screen, latency).
- severity: 0 none, 1 minor, 2 moderate, 3 serious, 4 critical.
- confidence: 0..1; if below 0.6 you are guessing - omit the issue instead.

Output ONLY minified JSON, no prose, no code fence, exactly this shape:
{"issues":[{"heuristic":"H4 consistency","description":"<one specific sentence>","evidence":"<exact visible text or region>","severity":2,"confidence":0.8,"fix":"<concrete change>"}],"working_well":["<short>"]}
"""


def load_prompt(prompt_file: str | None) -> str:
    """Return the critique prompt: DEFAULT_PROMPT, or the contents of prompt_file if given."""
    if prompt_file is None:
        return DEFAULT_PROMPT
    return Path(prompt_file).read_text(encoding="utf-8")


def _find_run_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    runs = sorted(RUNTIME_ROOT.glob("*-qa"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        sys.exit("no -qa run dir found; run qa.py first or pass --run-dir")
    return runs[0]


def _extract_json(text: str) -> dict | None:
    """Pull the first balanced {...} object out of claude's stdout (it may wrap
    in prose or a ```json fence)."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def critique(route: str, png: Path, prompt_template: str) -> dict:
    prompt = prompt_template.replace("<<ROUTE>>", route).replace("<<PATH>>", str(png))
    try:
        proc = subprocess.run(
            ["claude", "-p", "--allowedTools", "Read"],
            input=prompt, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"route": route, "error": "claude timeout", "issues": [], "working_well": []}
    parsed = _extract_json(proc.stdout)
    if parsed is None:
        return {"route": route, "error": "no JSON in output", "raw": proc.stdout[-300:],
                "issues": [], "working_well": []}
    result = {"route": route,
              "issues": parsed.get("issues", []) or [],
              "working_well": parsed.get("working_well", []) or []}
    if "scorecard" in parsed:
        result["scorecard"] = parsed["scorecard"]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", help="qa run dir to critique (default: latest -qa)")
    ap.add_argument("--only", help="single entry id (screenshot stem)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--min-confidence", type=float, default=0.6)
    ap.add_argument("--min-severity", type=int, default=1)
    ap.add_argument(
        "--prompt-file",
        default=None,
        help="Path to a custom critique prompt, overriding the built-in Nielsen-heuristics prompt.",
    )
    args = ap.parse_args()

    prompt_template = load_prompt(args.prompt_file)
    run_dir = _find_run_dir(args.run_dir)
    shots = sorted((run_dir / "screenshots").glob("*.png"))
    if args.only:
        shots = [s for s in shots if s.stem == args.only]
    if args.limit:
        shots = shots[: args.limit]
    if not shots:
        sys.exit(f"no screenshots in {run_dir}/screenshots")

    print(f"[vision] critiquing {len(shots)} screenshots from {run_dir.name}")
    results: list[dict] = []
    for png in shots:
        r = critique(png.stem, png, prompt_template)
        # keep only grounded, confident, non-trivial issues
        r["issues"] = [
            i for i in r["issues"]
            if isinstance(i, dict)
            and (i.get("confidence") or 0) >= args.min_confidence
            and (i.get("severity") or 0) >= args.min_severity
            and i.get("evidence")
        ]
        results.append(r)
        n = len(r["issues"])
        flag = "!" if r.get("error") else ("*" if n else " ")
        print(f"  {flag} {png.stem:<26} {n} issue(s)" + (f"  [{r['error']}]" if r.get("error") else ""))

    # severity-ranked report
    out_dir = run_dir
    all_issues = [(r["route"], i) for r in results for i in r["issues"]]
    all_issues.sort(key=lambda ri: ri[1].get("severity", 0), reverse=True)
    lines = [f"# Vision usability critique - {dt.datetime.now(dt.UTC).replace(tzinfo=None).isoformat()}Z",
             f"\nFrom `{run_dir}` - {len(shots)} screens - {len(all_issues)} grounded issues "
             f"(confidence >= {args.min_confidence}, severity >= {args.min_severity})\n"]
    SEV = {4: "CRITICAL", 3: "SERIOUS", 2: "MODERATE", 1: "MINOR"}
    for route, i in all_issues:
        lines.append(f"- **{SEV.get(i.get('severity',0),'?')}** `{route}` [{i.get('heuristic','?')}] "
                     f"- {i.get('description','')}  \n"
                     f"  evidence: _{i.get('evidence','')}_ - fix: {i.get('fix','')} "
                     f"(conf {i.get('confidence','?')})")
    (out_dir / "vision-report.md").write_text("\n".join(lines))
    (out_dir / "vision-manifest.json").write_text(json.dumps(
        {"generated_at": dt.datetime.now(dt.UTC).replace(tzinfo=None).isoformat() + "Z", "run_dir": str(run_dir),
         "min_confidence": args.min_confidence, "results": results}, indent=2))

    serious = sum(1 for _, i in all_issues if i.get("severity", 0) >= 3)
    digest = (f"vision: {serious} serious + {len(all_issues)-serious} minor UX issue(s) "
              f"across {len(shots)} screens" if all_issues
              else f"vision: no grounded UX issues across {len(shots)} screens")
    (out_dir / "vision-digest-line.txt").write_text(digest + "\n")
    print(f"\n{digest}\nreport: {out_dir / 'vision-report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
