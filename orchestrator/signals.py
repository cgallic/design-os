"""Load the design-os watchlist."""
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class Target:
    id: str
    url: str | None
    watch_dir: str | None
    vertical: str
    brand_pack: str | None


def load_watchlist(path: Path) -> list[Target]:
    """Parse watchlist.yaml into a list of Target."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    targets = []
    for entry in data["targets"]:
        targets.append(
            Target(
                id=entry["id"],
                url=entry.get("url"),
                watch_dir=entry.get("watch_dir"),
                vertical=entry["vertical"],
                brand_pack=entry.get("brand_pack"),
            )
        )
    return targets
