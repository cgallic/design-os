from pathlib import Path
from design_os.orchestrator.signals import Target, load_watchlist

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_watchlist_parses_url_target():
    targets = load_watchlist(FIXTURES / "watchlist.yaml")
    homepage = next(t for t in targets if t.id == "kaicalls-homepage")
    assert homepage.url == "https://kaicalls.com"
    assert homepage.vertical == "b2c-fintech"
    assert homepage.brand_pack == "visual-factory-kit/brand-packs/kaicalls"
    assert homepage.watch_dir is None


def test_load_watchlist_parses_watch_dir_target():
    targets = load_watchlist(FIXTURES / "watchlist.yaml")
    factory = next(t for t in targets if t.id == "factory-output")
    assert factory.watch_dir == "/path/to/cmo-os/factory/output"
    assert factory.url is None


def test_load_watchlist_returns_two_targets():
    assert len(load_watchlist(FIXTURES / "watchlist.yaml")) == 2
