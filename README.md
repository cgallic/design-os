# design-os

Autonomous design-quality loop **and design harness**. Composes kai-taste's
rubric, a render+critique pipeline (vendored from ux-qa-harness), and an
approval-gated shipping queue (vendored from approval-inbox) into a scheduled
pipeline — and, on top of that, enforces a researched canon of design mastery
as machine-checkable rules:

- `design_os/canon/` — distilled philosophies/workflows of the masters (Rams,
  Swiss school, Refactoring UI, Linear/Stripe/Vercel, Apple HIG, brand identity,
  typography, system governance, critique practice, motion, information design)
- `design_os/rules/catalog.yaml` — every rule with a stable ID, threshold,
  severity (`block`/`flag`/`advise`) and check type (`deterministic`/`vision`/`process`)
- `design_os/lint/` — deterministic rules computed over a live style snapshot
- `design_os/critique/lenses.py` — three-lens critique panel returning per-rule
  verdicts with evidence
- `design_os/process/` — workflow stage gates (divergence before convergence,
  taste contracts instead of adjectives, critique before ship)
- `waivers.yaml` — the only sanctioned way to break a rule: scoped, justified,
  expiring

The iron rule, enforced in `orchestrator/run.py`: an unwaived `block` failure
never auto-ships. See `AGENTS.md` for the full harness contract.

Ships as a single self-contained Python package — no sibling repos to clone,
no setup scripts to patch missing packaging metadata. `design_os/_vendor/`
carries a pinned copy of the two pieces design-os actually calls
(ux-qa-harness's `qa.py`/`vision.py` render+critique engine, approval-inbox's
`ApprovalStore`); `design_os/taste/kai-taste/` carries the kai-taste rubric
content directly. These are vendored, not live-synced — if the upstream
repos change, re-copy the relevant files by hand.

See `docs/superpowers/specs/2026-07-02-design-os-design.md` for the design.

## Setup
```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
```

## Run
```bash
design-os --watchlist watchlist.yaml --dry-run
```

The live (non-dry-run) path is not yet implemented — see `deploy/README.md`.


---

*Built and maintained by [Connor Gallic](https://pr.linkedin.com/in/cgallic) — connect on LinkedIn.*
