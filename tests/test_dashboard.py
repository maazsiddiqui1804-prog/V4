"""App logic (plain-English to-dos) and that the app renders every page."""
import datetime as dt
import json

import pytest

from v4 import app_logic as L


def test_todos_list_this_months_buys_and_actions(tmp_path):
    (tmp_path / "briefs").mkdir()
    (tmp_path / "briefs" / "2026-12.json").write_text(json.dumps({
        "month": "2026-12", "amount": 25000, "regime": "normal", "leftover": 0, "notes": [],
        "buys": [{"symbol": "MCX", "shares": 3, "amount": 12000, "limit": 4010.5, "rank": 1}],
        "holdings": [{"symbol": "OLD", "action": "SELL", "reason": "failed filters", "shares": 10},
                     {"symbol": "KEEP", "action": "HOLD", "reason": "", "shares": 0}]}))
    c = L.cfg()
    t = L.todos(dt.date(2026, 12, 5), data=tmp_path, c=c)
    assert t[0].startswith("Buy 3 MCX") and "₹4,010.50" in t[0]
    assert any(x.startswith("Sell 10 shares OLD") for x in t) and not any("KEEP" in x for x in t)
    assert any("Screener export" in x for x in t)                      # December import not done in this sandbox
    assert L.todos(dt.date(2026, 11, 10), data=tmp_path, c=c) == []      # nothing before the first brief month


def test_coming_up_starts_at_first_brief_month():
    c = L.cfg()
    up = dict(L.coming_up(dt.date(2026, 11, 10), c=c))
    assert "1 Dec" in up and "1 Jan" in up and "After the GMAT" in up


def test_waiting_items_and_status():
    w = " ".join(L.waiting())
    assert "W-8BEN" in w and "Approve the US numbers" in w
    s = L.status()
    assert set(s) == {"India investing", "US investing", "Trading"}


st = pytest.importorskip("streamlit")


def test_app_renders_default_page():
    """Every page is also screenshot-checked at phone size before each release (Playwright)."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("../dashboard/app.py", default_timeout=90).run()
    assert not at.exception, at.exception


def test_github_key_renewal_shows_45_days_before():
    c = L.cfg()
    assert not any("GitHub key" in w for _, w in L.coming_up(dt.date(2027, 9, 10), c=c))
    assert any("GitHub key" in w for _, w in L.coming_up(dt.date(2027, 9, 20), c=c))


def test_strategy_page_logic():
    from v4 import strategy_logic as S
    c = L.cfg()
    p = S.philosophy(c)
    assert set(p) == set(S.BUCKETS) and "52-week" in p["India Trading"]["rules"][0]
    srcs = S.trade_sources(c)
    if srcs:
        t = S.enrich(next(iter(srcs.values())))
        b = S.breakdown(t, "How it ended")
        assert b["Trades"].sum() == len(t)
        assert S.rule_checks(t)[0][0] == "Average result per trade"
    assert S.reason_label("debt-to-equity 2.10 > 1.5") == "Too much debt"
    assert S.reason_label("interest cover missing") == "Data missing: interest cover"
