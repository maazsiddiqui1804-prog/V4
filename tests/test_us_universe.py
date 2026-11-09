"""Checks the US universe rule without contacting SEC or Tiingo."""
import pytest
from v4.engines.us import universe as u


@pytest.fixture
def fake(monkeypatch):
    profiles = {
        1: dict(name="Chip Co", sic="3674", exchanges="Nasdaq"),
        2: dict(name="Retail Giant", sic="5961", exchanges="Nasdaq"),     # wrong industry
        3: dict(name="Small Soft", sic="7372", exchanges="NYSE"),         # too small
        4: dict(name="Foreign Fab", sic="3674", exchanges="NYSE,OTC"),    # 20-F: no float reported
        5: dict(name="OTC Only", sic="7372", exchanges="OTC"),            # wrong exchange
        6: dict(name="Big Utility", sic="4911", exchanges="NYSE"),
    }
    monkeypatch.setattr(u.sec, "ticker_map", lambda: {"CHIP": 1, "RTL": 2, "SMOL": 3, "FAB": 4, "OTCX": 5, "UTIL": 6})
    monkeypatch.setattr(u.sec, "profile", lambda cik: dict(profiles[cik], cik=cik))
    monkeypatch.setattr(u, "public_floats", lambda periods: {1: 3e11, 2: 9e11, 3: 1e9, 5: 5e10, 6: 4e10})
    monkeypatch.setattr(u, "shares_outstanding", lambda cik: {1: 1e9, 4: 5e9, 6: 1e9}.get(cik))
    monkeypatch.setattr(u, "tiingo_close", lambda t: {"CHIP": 300.0, "FAB": 50.0, "UTIL": 8.0}.get(t))


def test_rule_keeps_only_ai_codes_large_and_listed(fake):
    rows, stats = u.build(["CY2026Q2I"])
    assert [r["ticker"] for r in rows] == ["CHIP", "FAB"]       # $300B, then $250B (20-F filer kept)
    assert stats["after_industry"] == 3                         # CHIP, FAB, UTIL


def test_utility_below_floor_is_out(fake):
    rows, _ = u.build(["CY2026Q2I"])
    assert "UTIL" not in [r["ticker"] for r in rows]           # 1e9 shares x $8 = $8B < $10B


def test_blocklist_removes_name(fake, monkeypatch):
    real = u.load_rule
    monkeypatch.setattr(u, "load_rule", lambda: {**real(), "zerodha_blocklist": ["CHIP"]})
    rows, stats = u.build(["CY2026Q2I"])
    assert "CHIP" not in [r["ticker"] for r in rows] and stats["blocked"] == 1


def test_save_keeps_kite_check_marks(tmp_path):
    p = tmp_path / "u.csv"
    u.save([{"ticker": "A", "zerodha_checked": ""}], p)
    p.write_text(p.read_text().replace("A,\n", "A,yes\n").replace("A,\r\n", "A,yes\r\n"))
    u.save([{"ticker": "A", "zerodha_checked": ""}, {"ticker": "B", "zerodha_checked": ""}], p)
    assert "A,yes" in p.read_text()
