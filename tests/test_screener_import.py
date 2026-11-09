"""Checks the monthly India import on tiny made-up files."""
from v4.importers.screener import import_month
from v4.db import connect

NIFTY = """Company Name,Industry,Symbol,Series,ISIN Code
Good Co Ltd.,Capital Goods,GOOD,EQ,INE000A01001
Bank Ltd.,Financial Services,BANK,EQ,INE000B01001
Some REIT,Realty,REIT,RR,INE000C01001
Dummy X Ltd.,Capital Goods,DUMMYX,EQ,DUM000A01001
Missing Co,Healthcare,MISS,EQ,INE000D01001
"""
SCREENER = """Name,NSE Code,ISIN Code,Industry,Current Price,Price to Earning,Debt to equity
Good Co,GOOD,INE000A01001,Machinery,100,20,0.1
Bank,BANK,INE000B01001,Banks,50,,
Some REIT,REIT,INE000C01001,REIT,300,40,0.5
Other,OTHER,INE999Z01001,Misc,10,5,0
"""


def run(tmp_path, as_of="2026-11-09"):
    (tmp_path / "n.csv").write_text(NIFTY)
    (tmp_path / "s.csv").write_text(SCREENER)
    return import_month(tmp_path / "n.csv", tmp_path / "s.csv", as_of, tmp_path / "t.sqlite")


def test_universe_and_matching(tmp_path):
    rep = run(tmp_path)
    assert rep.universe == 4            # dummy row ignored
    assert rep.financials == 1 and rep.reits == 1
    assert rep.matched == 3
    assert rep.unmatched == ["MISS"]


def test_only_index_members_stored(tmp_path):
    run(tmp_path)
    with connect(tmp_path / "t.sqlite") as c:
        syms = {r[0] for r in c.execute("SELECT symbol FROM securities")}
        assert "OTHER" not in syms and "DUMMYX" not in syms
        assert c.execute("SELECT is_financial FROM securities WHERE symbol='BANK'").fetchone()[0] == 1


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
        assert c.execute("SELECT COUNT(*) FROM fundamentals WHERE metric='price_to_earning'").fetchone()[0] == 2


def test_report_lists_missing_columns(tmp_path):
    rep = run(tmp_path)
    assert "pledged_percentage" in rep.missing_required
