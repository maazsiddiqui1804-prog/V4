"""Checks the Console holdings importer on a made-up file in Zerodha's layout."""
import openpyxl
import pytest

from v4.importers import holdings as h
from v4.db import connect

HEADER_EQ = ["", "Symbol", "ISIN", "Sector", "Quantity Available", "Quantity Discrepant",
             "Quantity Long Term", "Quantity Pledged (Margin)", "Quantity Pledged (Loan)",
             "Average Price", "Previous Closing Price", "Unrealized P&L", "Unrealized P&L Pct."]
HEADER_MF = ["", "Symbol", "ISIN", "Instrument Type", "Quantity Available", "Quantity Discrepant",
             "Quantity Pledged (Margin)", "Quantity Pledged (Loan)", "Average Price",
             "Previous Closing Price", "Unrealized P&L", "Unrealized P&L Pct."]


def make_file(path, eq_rows, mf_rows=()):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, header, rows in (("Equity", HEADER_EQ, eq_rows), ("Mutual Funds", HEADER_MF, mf_rows),
                               ("Combined", HEADER_EQ, eq_rows)):
        ws = wb.create_sheet(name)
        ws.append([])
        ws.append(["", "Client ID", "XX0000"])
        ws.append(["", "Summary"])
        ws.append(["", "Invested Value", 1.0])
        ws.append([])
        ws.append(header)
        for r in rows:
            ws.append([""] + list(r))
    wb.save(path)


EQ = [
    ("ALPHA", "INE000A01001", "IT", 10, 0, 10, 0, 0, 100.0, 110.0, 100.0, 10.0),
    ("FUNDX-E", "INF000Z01001", "ETF", 5, 0, 0, 2, 0, 50.0, 51.0, 5.0, 2.0),
    ("SOLD", "INE000S01001", "IT", 0, 0, 0, 0, 0, 0, 0, 0, 0),
]
MF = [("LIQUIDFUND", "INF000L01001", "Debt", 3.5, 0, 0, 0, 1000.0, 1001.0, 3.5, 0.1)]


def test_detects_holdings_file(tmp_path):
    p = tmp_path / "holdings-XX0000.xlsx"
    make_file(p, EQ, MF)
    assert h.is_holdings_file(p)
    (tmp_path / "x.xlsx").write_bytes(b"not a workbook")
    assert not h.is_holdings_file(tmp_path / "x.xlsx")


def test_imports_equity_and_mf_not_combined(tmp_path):
    p = tmp_path / "h.xlsx"
    make_file(p, EQ, MF)
    db = tmp_path / "t.sqlite"
    with connect(db) as c:
        pass
    h.init_db(db)
    with connect(db) as c:   # ALPHA already known from the Nifty 500 import
        c.execute("INSERT INTO securities (market, symbol, isin) VALUES ('IN', 'ALPHA', 'INE000A01001')")
    rep = h.import_holdings(p, "2026-12-01", db)
    assert rep.positions == 3                     # ALPHA, FUNDX, LIQUIDFUND; SOLD (0 qty) skipped
    with connect(db) as c:
        rows = dict(c.execute("""SELECT s.symbol, hs.quantity FROM holdings_snapshots hs
                                 JOIN securities s USING(security_id)""").fetchall())
    assert rows == {"ALPHA": 10, "FUNDX": 7, "LIQUIDFUND": 3.5}   # pledged counted, '-E' stripped


def test_pledged_is_flagged(tmp_path):
    p = tmp_path / "h.xlsx"
    make_file(p, EQ)
    rep = h.import_holdings(p, "2026-12-01", tmp_path / "t.sqlite")
    assert any("FUNDX" in w and "pledged" in w for w in rep.warnings)


def test_reimport_same_day_replaces(tmp_path):
    p = tmp_path / "h.xlsx"
    make_file(p, EQ)
    db = tmp_path / "t.sqlite"
    h.import_holdings(p, "2026-12-01", db)
    h.import_holdings(p, "2026-12-01", db)
    with connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM holdings_snapshots").fetchone()[0] == 2
