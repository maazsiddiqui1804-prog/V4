"""Checks the AMFI NAV parsing and recording without contacting AMFI."""
import pytest
from v4.importers import benchmarks as bm

SAMPLE = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date

Open Ended Schemes(Other Scheme - Index Funds)

Some Mutual Fund
111;INE1;-;Alpha Nifty 500 Index Fund - Direct Plan - Growth;Direct;Growth;15.50;06-Nov-2026
112;INE2;-;Alpha Nifty 500 Index Fund - Regular Plan - Growth;Regular;Growth;15.10;06-Nov-2026
113;INE3;-;Alpha Nifty 500 Momentum 50 Index Fund - Direct Plan - Growth;Direct;Growth;9.80;06-Nov-2026
221;INE4;-;Beta Nifty200 Quality 30 Index Fund - Direct Plan - Growth;Direct;Growth;12.00;06-Nov-2026
222;INE5;-;Beta Nifty200 Quality 30 Index Fund - Direct Plan - IDCW;Direct;IDCW;12.00;06-Nov-2026
331;INE6;-;Gamma Nasdaq 100 Fund of Fund - Direct Plan Growth;Direct;Growth;30.25;06-Nov-2026
999;INE7;-;Broken Fund;Direct;Growth;N.A.;06-Nov-2026
"""
CFG = {
    "nifty500": {"label": "x", "match": r"nifty\s*500\s*index", "exclude": "momentum", "scheme_codes": ["111"]},
    "quality30": {"label": "x", "match": r"nifty\s*200\s*quality\s*30", "scheme_codes": ["221"]},
    "nasdaq100": {"label": "x", "match": r"nasdaq\s*100", "scheme_codes": ["331"]},
}


def test_parse_skips_headings_and_bad_navs():
    rows = bm.parse_amfi(SAMPLE)
    codes = {r["scheme_code"] for r in rows}
    assert "999" not in codes and "111" in codes
    assert next(r for r in rows if r["scheme_code"] == "111")["date"] == "2026-11-06"


def test_discover_keeps_direct_growth_only():
    found = bm.discover(bm.parse_amfi(SAMPLE), CFG)
    assert [r["scheme_code"] for r in found["nifty500"]] == ["111"]   # not regular, not momentum
    assert [r["scheme_code"] for r in found["quality30"]] == ["221"]  # not IDCW


def test_record_appends_once(tmp_path):
    p = tmp_path / "navs.csv"
    rows = bm.parse_amfi(SAMPLE)
    assert bm.record(rows, CFG, p) == 3
    assert bm.record(rows, CFG, p) == 0          # same day again: no duplicates
    assert len(p.read_text().strip().splitlines()) == 4


def test_missing_fund_fails_loudly(tmp_path):
    cfg = dict(CFG, nifty500=dict(CFG["nifty500"], scheme_codes=["404"]))
    with pytest.raises(RuntimeError, match="404"):
        bm.record(bm.parse_amfi(SAMPLE), cfg, tmp_path / "navs.csv")


def test_load_into_db(tmp_path):
    p = tmp_path / "navs.csv"
    bm.record(bm.parse_amfi(SAMPLE), CFG, p)
    assert bm.load_into_db(p, tmp_path / "t.sqlite") == 3
