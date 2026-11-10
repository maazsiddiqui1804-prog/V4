"""Checks the US universe rule without contacting SEC or Tiingo."""
import pytest
from v4.engines.us import universe as u


@pytest.fixture
def fake(monkeypatch):
    profiles = {
        1: dict(name="Chip Co", sic="3674", exchanges="Nasdaq"),
        2: dict(name="Retail Giant", sic="5961", exchanges="Nasdaq"),     # wrong industry
        3: dict(name="Small Soft", sic="7372", exchanges="NYSE"),         # too small
        4: dict(name="Foreign Fab", sic="3674", exchanges="NYSE,OTC", forms=["20-F", "6-K"]),    # 20-F: no float reported
        5: dict(name="OTC Only", sic="7372", exchanges="OTC"),            # wrong exchange
        6: dict(name="Big Utility", sic="4911", exchanges="NYSE"),
    }
    monkeypatch.setattr(u.sec, "ticker_map", lambda: {"CHIP": 1, "RTL": 2, "SMOL": 3, "FAB": 4, "OTCX": 5, "UTIL": 6})
    monkeypatch.setattr(u.sec, "profile", lambda cik: dict(profiles[cik], cik=cik))
    monkeypatch.setattr(u, "public_floats", lambda periods: {1: 3e11, 2: 9e11, 3: 1e9, 5: 5e10, 6: 4e10})
    monkeypatch.setattr(u, "shares_outstanding", lambda cik: {1: 1e9, 4: 5e9, 6: 1e9}.get(cik))


def test_rule_keeps_only_ai_codes_large_and_listed(fake):
    rows, stats = u.build(["CY2026Q2I"])
    assert [r["ticker"] for r in rows] == ["CHIP", "UTIL", "FAB"]   # floats $300B, $40B; foreign filer size unknown
    assert stats["after_industry"] == 3 and stats["size_to_confirm"] == 1


def test_small_float_is_out(fake):
    rows, _ = u.build(["CY2026Q2I"])
    assert "SMOL" not in [r["ticker"] for r in rows]           # float $1B < $10B


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


def test_no_tiingo_in_universe_build(fake):
    """D-135: the universe build uses SEC only; Tiingo is called only for Kite-confirmed names."""
    import inspect
    src = inspect.getsource(u)
    assert "api.tiingo.com" not in src and "TIINGO_API_KEY" not in src
    rows, _ = u.build(["CY2026Q2I"])
    assert len(rows) == 3


def test_blank_tickers_ignored(fake, monkeypatch):
    monkeypatch.setattr(u.sec, "ticker_map", lambda: {"CHIP": 1, "": 6, "UTIL": 6})
    rows, _ = u.build(["CY2026Q2I"])
    assert "" not in [r["ticker"] for r in rows]


def test_foreign_issuer_needs_20f_or_40f():
    from v4.engines.us.universe import is_foreign_issuer
    assert is_foreign_issuer({"forms": ["20-F", "6-K"]})
    assert is_foreign_issuer({"forms": ["40-F"]})
    assert not is_foreign_issuer({"forms": ["10-K", "8-K"]})      # e.g. a utility subsidiary with listed debt only
    assert not is_foreign_issuer({})
