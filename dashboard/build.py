"""design-os's own SQLite store and self-contained static dashboard."""
from pathlib import Path
import sqlite3

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def grade_for_score(score: int) -> str:
    """Map a kai-taste composite score (/30) to its A-F grade band."""
    if score >= 25:
        return "A"
    if score >= 20:
        return "B"
    if score >= 15:
        return "C"
    if score >= 10:
        return "D"
    return "F"


def init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()


def record_run(db_path: Path, result: dict) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO runs (target_id, final_score, taste_grade, iterations, gate, item_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (
            result["target_id"],
            result["final_score"],
            grade_for_score(result["final_score"]),
            result["iterations"],
            result["gate"],
            result["item_id"],
        ),
    )
    conn.commit()
    conn.close()


def render_dashboard(db_path: Path, out_html_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT target_id, final_score, taste_grade, iterations, gate, created_at "
        "FROM runs ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    rows_html = "\n".join(
        f"<tr><td>{target_id}</td><td>{score}/30</td><td>{grade}</td>"
        f"<td>{iterations}</td><td>{gate}</td><td>{created_at}</td></tr>"
        for target_id, score, grade, iterations, gate, created_at in rows
    )
    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>design-os dashboard</title></head>
<body>
<h1>design-os — recent runs</h1>
<table border="1">
<tr><th>Target</th><th>Score</th><th>Grade</th><th>Iterations</th><th>Gate</th><th>Run at</th></tr>
{rows_html}
</table>
</body>
</html>
"""
    Path(out_html_path).write_text(html, encoding="utf-8")
