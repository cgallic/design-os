from datetime import datetime, timedelta
from orchestrator.signals import Target
from orchestrator.detect import due_targets

T1 = Target(id="a", url="https://a.example", watch_dir=None, vertical="b2b-saas", brand_pack="bp/a")
T2 = Target(id="b", url="https://b.example", watch_dir=None, vertical="b2b-saas", brand_pack="bp/b")


def test_due_targets_includes_never_run_targets():
    now = datetime(2026, 7, 2, 12, 0, 0)
    result = due_targets([T1, T2], last_run={}, now=now, sweep_interval=timedelta(days=7))
    assert {t.id for t in result} == {"a", "b"}


def test_due_targets_excludes_recently_run_targets():
    now = datetime(2026, 7, 2, 12, 0, 0)
    last_run = {"a": now - timedelta(days=1), "b": now - timedelta(days=10)}
    result = due_targets([T1, T2], last_run=last_run, now=now, sweep_interval=timedelta(days=7))
    assert {t.id for t in result} == {"b"}
