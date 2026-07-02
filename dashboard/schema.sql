PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id TEXT NOT NULL,
    final_score INTEGER NOT NULL,
    taste_grade TEXT NOT NULL,
    iterations INTEGER NOT NULL,
    gate TEXT NOT NULL CHECK(gate IN ('safe', 'irreversible')),
    item_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
