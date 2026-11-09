"""The one shared V4 database (D-001, D-111).

Plain English: this file opens data/v4.sqlite and makes sure every table exists.
Running it twice is safe — it never deletes or overwrites data.
"""
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "v4.sqlite"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Columns added after a table was first created. CREATE TABLE IF NOT EXISTS
# won't add them to an existing database, so they're added here, once.
MIGRATIONS = [
    ("securities", "is_reit", "INTEGER NOT NULL DEFAULT 0"),  # D-115
]


def init_db(path: Path = DB_PATH) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        for table, col, decl in MIGRATIONS:
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
