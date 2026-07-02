"""Decide which targets are due for a design-os pass."""
from datetime import datetime, timedelta
from design_os.orchestrator.signals import Target


def due_targets(
    targets: list[Target],
    last_run: dict[str, datetime],
    now: datetime,
    sweep_interval: timedelta,
) -> list[Target]:
    """Return targets never run, or last run before now - sweep_interval."""
    cutoff = now - sweep_interval
    result = []
    for target in targets:
        last = last_run.get(target.id)
        if last is None or last < cutoff:
            result.append(target)
    return result
