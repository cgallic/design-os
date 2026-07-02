# design-os deploy

> **Scope note:** the live path audits real URL targets end-to-end (real Playwright
> render, real Claude critique against the kai-taste rubric, real approval-inbox item,
> real dashboard row) — verified against a real target. It does not yet auto-repair
> findings (design-os can only observe a live URL, not rewrite it) and does not yet
> support `watch_dir` targets (factory-output re-render integration is undesigned) —
> those are skipped with a `SKIP:` log line, not silently dropped.

Source templates only — install on the target box via:

```bash
mkdir -p ~/.config/systemd/user
cp design-audit.service design-audit.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now design-audit.timer
```

Requires `~/.config/design-os/env` with any secrets `orchestrator/run.py`'s
live path needs (Claude CLI auth, etc.) — not committed to this repo.

Follows the same oneshot+timer template as cmo-os/deploy/.
