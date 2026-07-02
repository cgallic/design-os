# design-os

Autonomous design-quality loop. Composes kai-taste (rubric), ux-qa-harness
(render+critique), visual-factory-kit (brand tokens), approval-inbox (gate),
and cmo-daily-dashboard (dashboard schema) into a scheduled pipeline.

See `docs/superpowers/specs/2026-07-02-design-os-design.md` for the design.

## Setup
```bash
python -m venv .venv
.venv/Scripts/python scripts/setup_siblings.py
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python scripts/verify_deps.py
```
`scripts/setup_siblings.py` exists because some sibling repos lack packaging
metadata for editable installs; it supplies committed, reproducible patches
(from `sibling-patches/`) for those.
