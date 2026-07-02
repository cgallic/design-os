# design-os

Autonomous design-quality loop. Composes kai-taste's rubric, a render+critique
pipeline (vendored from ux-qa-harness), and an approval-gated shipping queue
(vendored from approval-inbox) into a scheduled pipeline.

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
