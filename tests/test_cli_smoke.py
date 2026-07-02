import subprocess
import sys
from pathlib import Path

WATCHLIST = Path(__file__).parent / "fixtures" / "watchlist.yaml"


def test_dry_run_lists_due_targets():
    result = subprocess.run(
        [sys.executable, "-m", "orchestrator.run", "--watchlist", str(WATCHLIST), "--dry-run"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "DUE: kaicalls-homepage" in result.stdout
    assert "DUE: factory-output" in result.stdout
