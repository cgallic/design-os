# design-os deploy

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
