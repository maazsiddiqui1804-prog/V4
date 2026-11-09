"""Checks the monthly India import on tiny made-up files."""
from v4.importers.screener import import_month
from v4.db import connect

NIFTY = """Company Name,Industry,Symbol,Series,ISIN Code
Good Co Ltd.,Capital Goods,GOOD,EQ,INE000A01001
Bank Ltd.,Financial Services,BANK,EQ,INE000B01001
Exchange Ltd.,Financial Services,EXCH,EQ,INE000E01001
Some REIT,Realty,REIT,RR,INE000C01001
Dummy X Ltd.,Capital Goods,DUMMYX,EQ,DUM000A01001
Missing Co,Healthcare,MISS,EQ,INE000D01001
"""
SCREENER = """Name,NSE Code,ISIN Code,Industry Group,Industry,Current Price,Price to Earning,Debt to equity
Good Co,GOOD,INE000A01001,Machinery,Machinery,100,20,0.1
Bank,BANK,INE000B01001,Banks,Banks,50,,
Exchange,EXCH,INE000E01001,Capital Markets,Exchange,900,45,0
Some REIT,REIT,INE000C01001,Realty,REIT,300,40,0.5
Other,OTHER,INE999Z01001,Misc,Misc,10,5,0
"""


def run(tmp_path, as_of="2026-11-09"):
    (tmp_path / "n.csv").write_text(NIFTY)
    (tmp_path / "s.csv").write_text(SCREENER)
    return import_month(tmp_path / "n.csv", tmp_path / "s.csv", as_of, tmp_path / "t.sqlite")


def test_universe_and_matching(tmp_path):
    rep = run(tmp_path)
    assert rep.universe == 5            # dummy row ignored
    assert rep.financials == 1 and rep.financials_kept == 1 and rep.reits == 1
    assert rep.matched == 4
    assert rep.unmatched == ["MISS"]


def test_only_index_members_stored(tmp_path):
    run(tmp_path)
    with connect(tmp_path / "t.sqlite") as c:
        syms = {r[0] for r in c.execute("SELECT symbol FROM securities")}
        assert "OTHER" not in syms and "DUMMYX" not in syms
        flags = {r[0]: (r[1], r[2]) for r in c.execute("SELECT symbol, is_financial, is_reit FROM securities")}
        assert flags["BANK"] == (1, 0)      # bank excluded (D-114)
        assert flags["EXCH"] == (0, 0)      # exchange kept (D-114)
        assert flags["REIT"] == (0, 1)      # REIT excluded (D-115)
        assert flags["MISS"] == (0, 0)      # unmatched non-financial: not flagged


def test_numbers_stored_and_blanks_skipped(tmp_path):
    run(tmp_path)
    with connect(tmp_path / "t.sqlite") as c:
        pe = c.execute("""SELECT value FROM fundamentals f JOIN securities s USING(security_id)
                          WHERE s.symbol='GOOD' AND metric='price_to_earning'""").fetchone()[0]
        assert pe == 20
        assert c.execute("""SELECT COUNT(*) FROM fundamentals f JOIN securities s USING(security_id)
                            WHERE s.symbol='BANK' AND metric='price_to_earning'""").fetchone()[0] == 0
        assert c.execute("SELECT close FROM prices").fetchall()


def test_reimport_same_month_does_not_duplicate(tmp_path):
    run(tmp_path)
    run(tmp_path)
    with connect(tmp_path / "t.sqlite") as c:
        assert c.execute("SELECT COUNT(*) FROM fundamentals WHERE metric='price_to_earning'").fetchone()[0] == 3  # GOOD, EXCH, REIT; BANK has none


def test_report_lists_missing_columns(tmp_path):
    rep = run(tmp_path)
    assert "pledged_percentage" in rep.missing_required


def test_unmatched_nse_financial_is_excluded_cautiously(tmp_path):
    nifty = NIFTY + "Lost Lender Ltd.,Financial Services,LOST,EQ,INE000F01001\n"
    (tmp_path / "n.csv").write_text(nifty)
    (tmp_path / "s.csv").write_text(SCREENER)
    import_month(tmp_path / "n.csv", tmp_path / "s.csv", "2026-11-09", tmp_path / "t.sqlite")
    with connect(tmp_path / "t.sqlite") as c:
        assert c.execute("SELECT is_financial FROM securities WHERE symbol='LOST'").fetchone()[0] == 1


def test_old_database_gets_new_column(tmp_path):
    import sqlite3
    from v4.db import init_db
    db = tmp_path / "old.sqlite"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE securities (security_id INTEGER PRIMARY KEY, market TEXT, symbol TEXT, is_financial INTEGER)")
    init_db(db)
    with sqlite3.connect(db) as c:
        assert "is_reit" in {r[1] for r in c.execute("PRAGMA table_info(securities)")}


def test_one_year_of_profit_is_not_enough(tmp_path):
    # Regression: a single "Net Profit last year" column must not satisfy the 3-year loss check.
    scr = SCREENER.replace("Debt to equity\n", "Debt to equity,Net Profit last year\n", 1)
    scr = "\n".join(l + ",1" if i else l for i, l in enumerate(scr.strip().split("\n"))) + "\n"
    (tmp_path / "n.csv").write_text(NIFTY)
    (tmp_path / "s.csv").write_text(scr)
    rep = import_month(tmp_path / "n.csv", tmp_path / "s.csv", "2026-11-09", tmp_path / "t.sqlite")
    reasons = " ".join(rep.missing_required.values())
    assert "year before" in reasons and "2 years back" in reasons
    assert "latest year" not in reasons
