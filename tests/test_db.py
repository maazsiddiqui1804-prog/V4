"""Checks that the database builds, is safe to re-run, and enforces its basic rules."""
import sqlite3
import pytest
from v4.db import init_db, connect

EXPECTED = {
    "securities", "universe_membership", "prices", "fundamentals", "benchmark_levels",
    "fx_rates", "holdings_snapshots", "investment_lists", "trade_signals", "trades",
    "overrides", "red_flags", "runs",
}


def test_all_tables_created(tmp_path):
    db = tmp_path / "t.sqlite"
    init_db(db)
    with connect(db) as c:
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED <= names


def test_rerun_keeps_data(tmp_path):
    db = tmp_path / "t.sqlite"
    init_db(db)
    with connect(db) as c:
        c.execute("INSERT INTO securities (market, symbol) VALUES ('IN', 'TCS')")
    init_db(db)
    with connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM securities").fetchone()[0] == 1


def test_rejects_unknown_market(tmp_path):
    db = tmp_path / "t.sqlite"
    init_db(db)
    with connect(db) as c, pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO securities (market, symbol) VALUES ('UK', 'X')")


def test_trades_must_be_paper_or_live(tmp_path):
    db = tmp_path / "t.sqlite"
    init_db(db)
    with connect(db) as c:
        c.execute("INSERT INTO securities (market, symbol) VALUES ('IN', 'TCS')")
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO trades (security_id, mode) VALUES (1, 'yolo')")
