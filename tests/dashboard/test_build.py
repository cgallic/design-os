from pathlib import Path
from design_os.dashboard.build import init_db, record_run, render_dashboard, grade_for_score
import sqlite3


def test_grade_for_score_maps_kai_taste_bands():
    assert grade_for_score(28) == "A"
    assert grade_for_score(22) == "B"
    assert grade_for_score(17) == "C"
    assert grade_for_score(12) == "D"
    assert grade_for_score(5) == "F"


def test_init_db_creates_runs_table(tmp_path):
    db_path = tmp_path / "design-os.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "runs" in tables


def test_record_run_inserts_a_row(tmp_path):
    db_path = tmp_path / "design-os.db"
    init_db(db_path)
    record_run(db_path, {"target_id": "kaicalls-homepage", "final_score": 28, "iterations": 1, "gate": "safe", "item_id": "item-1"})
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT target_id, final_score, taste_grade FROM runs").fetchone()
    assert row == ("kaicalls-homepage", 28, "A")


def test_render_dashboard_writes_self_contained_html(tmp_path):
    db_path = tmp_path / "design-os.db"
    out_path = tmp_path / "index.html"
    init_db(db_path)
    record_run(db_path, {"target_id": "kaicalls-homepage", "final_score": 28, "iterations": 1, "gate": "safe", "item_id": "item-1"})

    render_dashboard(db_path, out_path)

    html = out_path.read_text(encoding="utf-8")
    assert "kaicalls-homepage" in html
    assert "A" in html
    assert "<html" in html
