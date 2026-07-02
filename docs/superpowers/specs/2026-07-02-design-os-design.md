# design-os — Design Spec

**Date:** 2026-07-02
**Status:** Draft, pending review

## 1. Problem

There is no autonomous design-quality loop anywhere in the stack. Every piece that could form one already exists but is invoked by hand:

- `kai-taste` (in `cgallic/kai-cmo-harness`) is a complete, production-ready design-taste rubric — Three Pillars scoring, 8 failure modes, 7 north-star metrics, an Audit protocol and a Design protocol, A–F grading — but it only runs when a human types `/kai-taste`.
- `ux-qa-harness` can render a live page/component with Playwright and run a vision-model critique over the screenshots, but its critique prompt is hardcoded to generic Nielsen heuristics, has no taste/brand dimension, and only runs when someone runs `qa.py`/`vision.py` by hand.
- `visual-factory-kit` can render on-brand assets deterministically from a brand pack, with its own QA gate, but only when someone runs `render.py`.
- `approval-inbox` and `cmo-daily-dashboard` are generic, already-genericized gate/dashboard primitives with no design-specific producer feeding them yet.
- `cmo-os/factory` generates themed pages today (per `docs/specs/2026-07-02-factory-multi-theme-design.md`) with mechanical gates (`deliberate_palette`, `premium_template`) but no taste-level or vision-based check.

**design-os is the scheduler and glue that chains these into a self-running loop.** It introduces no new rubric, no new renderer, no new gate primitive, and no new dashboard primitive. Its only new code is orchestration: decide what needs attention, run the existing tools in the right order, translate findings into repair actions, and gate the result.

## 2. Principles (adopted, not invented)

Pulled from `kai-taste` / `chatgpt_taste.md` (the credible core of the prior taste research — the other four research files in `cmo_agent/docs/research/taste/` are speculative and were deliberately not used as a source):

- **Iron law:** taste is subordinate to function. The moment a correction vector dominates user/business intent, the design has failed regardless of polish.
- **North-star metrics are kai-taste's, unchanged:** Refinement Velocity, Correction Density, Kinetic Friction, Time-to-Value, Correction Effort, Dismissal Rate, Clarification Burden. design-os's job is to drive these down over time and chart them — not to invent replacements.
- **Refiner Layer architecture** (kai-taste's 10-step Design Mode protocol) is the shape of design-os's core loop: generate → critique against explicit rubric → diff, not rewrite → re-render → gate. Section 4 below is this protocol made runnable.
- **Failure-mode vigilance over "more polish."** Oracle Polish and Cohesion Rigidity are explicit failure modes in the rubric — design-os's repair step must not blindly maximize the score; the critique pass scans all 8 failure modes every run, not just the 3 pillar scores.

## 3. What already exists (reuse table)

| Component | Repo | Role in design-os | Integration surface |
|---|---|---|---|
| Taste rubric | `cgallic/kai-cmo-harness` → `harness/skills/kai-taste/` | The critique prompt/rubric source. Read directly, not vendored. | `SKILL.md` + `references/pillar-rubrics.md` (markdown, loaded as prompt context) |
| Render + QA + critique | `cgallic/ux-qa-harness` | The render/critique engine | `qa.py` (Playwright render + console/a11y/visual-diff) writes `qa-manifest.json`; `vision.py` (Claude CLI critique over screenshots) writes `vision-report.md` + `vision-manifest.json`. design-os overrides `vision.py`'s hardcoded `PROMPT` constant with the kai-taste rubric (fork or `--prompt-file` patch — see §7). |
| Branded asset factory | `cgallic/visual-factory-kit` | Deterministic on-brand render + its own QA gate | `python -m visual_factory.render render --request R.json --brand brand-packs/X` → PNG + `.provenance.json` + `*-qa-report.json` |
| Approval gate | `cgallic/approval-inbox` | Safe/irreversible gate before anything ships | `ApprovalStore.add(item_dict) -> id`, `.transition(id, "approve"/"agent_do", actor=)`, schema in `schemas/approval-item.schema.json` |
| Dashboard | `cgallic/cmo-daily-dashboard` | Read-only control surface | SQLite schema (`items`/`runs`/`state`) + `python -m cmo_dashboard.build` → static `index.html` |
| Page generator | `cmo_agent/cmo-os/factory` | An artifact *source* design-os audits, not reimplements | Reads factory's output dir / `THEMES` registry results as an ingest signal |
| Vertical design knowledge | `cmo_agent/design/b2b-saas-design.md`, `b2c-fintech-design.md` | Reference-only context for the critique prompt, per vertical | Read-only |

design-os vendors none of this. It depends on all six as sibling checkouts/installs and calls into them via their documented CLI/API surfaces.

## 4. Core loop

Per artifact (a URL on the watchlist, a factory-generated page, a visual-factory-kit render, or a UI PR diff):

1. **Sense** — `orchestrator/signals.py` builds the work queue from `watchlist.yaml` (scheduled sweep) plus any new files dropped in factory's output dir since the last run.
2. **Render** — `critique/runner.py` shells out to `ux-qa-harness/qa.py` for the target route(s). This produces `qa-manifest.json` (console/a11y/visual-diff) and screenshots under `screenshots/`. ux-qa-harness's own Playwright pipeline is the sole renderer — design-os does not duplicate rendering logic.
3. **Critique** — `critique/runner.py` invokes `ux-qa-harness/vision.py` against the screenshots, with its prompt swapped for one built from `kai-taste/SKILL.md` + `references/pillar-rubrics.md` (see §7 for exactly how). Output: a scorecard per kai-taste's own template — pillar scores (/30 composite), 8-failure-mode scan, north-star metrics where computable, and a **Prioritized Fixes** table (P0/P1/P2).
4. **Repair** — `critique/repair_ops.py` walks the Prioritized Fixes table. Each finding maps to either:
   - a **deterministic fix** (contrast, token-snap, spacing-to-grid, affordance styling) — applied automatically, or
   - a **judgment fix** (copy rewrite, layout restructure, brand-voice call) — left as a flagged item, never auto-applied.
   Deterministic fixes trigger a re-render + re-critique. Capped at 3 iterations; on cap-out, the artifact ships to the gate at whatever state it's in, flagged as "iteration-capped."
5. **Gate** — `gate.py` calls `ApprovalStore.add()` with one row per artifact: `gate="safe"` (draft-only output, nothing live changes) auto-approves via `agent_do`; `gate="irreversible"` (touches a published/live surface) is left `pending` for a human. The item's `evidence[]` carries the kai-taste scorecard; `action.dry_run_preview` is the plain-English summary of what would ship.
6. **Dashboard** — `dashboard/build.py` extends `cmo_dashboard`'s schema with a `taste_grade` column and writes runs so `cmo-daily-dashboard`'s existing `index.html` generator picks them up unmodified. A trend view (Correction Cost proxies over time, per kai-taste's own metrics) is the one genuinely new UI element — everything else is the existing dashboard.

## 5. Repo layout

```
design-os/
  README.md
  AGENTS.md
  watchlist.yaml
  orchestrator/
    run.py              # sense -> render -> critique -> repair -> gate, one pass
    signals.py           # builds the work queue
    detect.py            # never-audited / stale detection (last-run timestamp per target)
  critique/
    runner.py            # wraps ux-qa-harness qa.py + vision.py, injects kai-taste rubric
    rubric_prompt.py      # builds the vision.py prompt from kai-taste SKILL.md + pillar-rubrics.md
    repair_ops.py         # Prioritized Fixes finding -> deterministic fix function, or flag
  gate.py                 # approval-inbox ApprovalStore calls, safe/irreversible mapping
  dashboard/
    build.py              # cmo_dashboard schema extension + build invocation
  deploy/
    design-audit.service
    design-audit.timer
  docs/
    superpowers/specs/2026-07-02-design-os-design.md   # this file
```

Python, matching every sibling repo. `requirements.txt` pins `ux-qa-harness`, `visual-factory-kit`, `approval-inbox`, `cmo-daily-dashboard` as local editable installs (`pip install -e ../ux-qa-harness` etc., siblings under `Desktop/dev/`) rather than PyPI packages, since none are published.

## 6. Rubric integration mechanics

`ux-qa-harness/vision.py` currently hardcodes a `PROMPT` constant (Nielsen heuristics, single screenshot per call) with no CLI flag to override it. design-os does not fork `ux-qa-harness`; instead `critique/rubric_prompt.py`:

1. Reads `kai-taste/SKILL.md`'s "Three Pillars", "Failure Modes", and "North Star Metrics" tables plus `references/pillar-rubrics.md`'s 1–10 criteria.
2. Composes a prompt that asks for the same JSON shape `vision.py` already expects (`{"issues":[...], "working_well":[...]}`) but with `issues[].heuristic` drawn from the pillar/failure-mode vocabulary instead of Nielsen's, and an added top-level `scorecard` object matching kai-taste's Audit Mode template (pillar scores, failure-mode scan, prioritized fixes).
3. Calls `vision.py`'s underlying `claude -p` subprocess pattern directly (reusing its screenshot-loading and manifest-writing code by importing it as a library, since it's a local sibling checkout) with the swapped prompt, rather than shelling out to the unmodified CLI.

This is the one place design-os writes non-trivial glue code — everywhere else it's pure orchestration.

## 7. Repair-ops catalog (v1)

| Finding pattern (from Prioritized Fixes) | Deterministic? | Fix |
|---|---|---|
| Contrast below 4.5:1 (normal text) / 3:1 (large text, UI components) | Yes | Darken/lighten to nearest passing brand-token color |
| Off-grid spacing (not on 4/8pt scale) | Yes | Snap to nearest token value |
| Affordance Collapse (button/link doesn't look interactive) | Yes | Apply the brand pack's standard button/link treatment |
| Cohesion Rigidity / off-token color or shadow | Yes | Replace with nearest design-token value |
| Touch target < 44×44px | Yes | Pad to minimum |
| Copy/tone issues, layout restructuring, brand-voice calls, anything under "judgment fix" in kai-taste's checklist | No | Flag only, surfaced in the gate item for human review |

Unmapped finding types default to "judgment fix" (never auto-applied) — the catalog only grows by adding rows, never by guessing.

## 8. Gating rules

- `gate="safe"`: output stayed in a draft/staging location (no live URL, no published page, no committed file outside a scratch/output dir). Auto-approved via `agent_do`.
- `gate="irreversible"`: output would touch a live/published surface (factory's reconciled live page, a deployed asset, a merged PR). Always `pending`, always waits for a human approve in `approval-inbox`.
- Iteration-capped artifacts (§4 step 4) are always at least `risk_tier="medium"` regardless of gate, so they're visible even when auto-approved.

## 9. Scheduling

Systemd `.service` + `.timer`, same template as `cmo-os/deploy/`: `Type=oneshot`, `EnvironmentFile` for secrets, weekly `OnCalendar` sweep of `watchlist.yaml` plus `Persistent=true`. A second, more frequent timer (e.g. every 15 min, matching `cmo-os`'s board-executor cadence) checks factory's output directory for newly generated pages and audits them on arrival rather than waiting for the weekly sweep.

## 10. watchlist.yaml format

```yaml
targets:
  - id: kaicalls-homepage
    url: https://kaicalls.com
    vertical: b2c-fintech   # selects which cmo_agent/design/*.md to load as context
    brand_pack: visual-factory-kit/brand-packs/kaicalls   # path to the canonical brand pack (see open question in §12)
  - id: factory-output
    watch_dir: /path/to/cmo-os/factory/output
    vertical: b2b-saas
cadence:
  sweep: weekly
  watch_dir_poll: 15m
```

## 11. Out of scope for v1

- No new rubric, scoring system, or metric — kai-taste's is used as-is.
- No new renderer — ux-qa-harness's Playwright pipeline only.
- No image generation — visual-factory-kit's deterministic templates only, no diffusion/generative imagery.
- No multi-agent panel/tournament judging (external research suggested this for diversity; not adopted in v1 — single critique pass per artifact, revisit if genericness becomes a measured problem).
- No SQLite inbox of design-os's own — reuses approval-inbox's and cmo-daily-dashboard's schemas directly rather than building a third one.
- No write access to factory's theme registry or live-page reconciliation — design-os observes and gates, factory's own pipeline still owns publishing mechanics.

## 12. Open questions

- Does `ux-qa-harness/vision.py`'s screenshot-loading code import cleanly as a library, or does it need a small refactor to expose a callable (vs. `__main__`-only)? Needs a spike before §6 is implementable as described.
- `cmo_dashboard.build`'s `_load_data()` hardcodes its SQLite path (`ROOT / "inbox.db"`) with no CLI override (per integration research, §"cmo-daily-dashboard"). design-os either writes to that literal path convention in its own directory or forks `_load_data` — decide during implementation, not architecture.
- Brand-pack source of truth: `visual-factory-kit`'s `brand-packs/` vs. any KaiCalls-specific tokens living elsewhere (`kaicalls-design` skill references its own token set) — needs reconciliation so design-os's contrast/token-snap repair ops read one canonical source per target.
