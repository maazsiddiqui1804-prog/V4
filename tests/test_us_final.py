"""Checks US momentum, PEG guardrail and the Nasdaq-100 fallback."""
import pandas as pd
import pytest
from v4.engines.us import final as fn

W = {"quality": 40, "growth": 30, "momentum": 30}


def test_returns_need_enough_history():
    closes = [(f"d{i}", 100 + i) for i in range(260)]
    r = fn.returns(closes)
    assert r["price"] == 359 and r["ret_6m"] == pytest.approx(359 / 233 - 1) and r["ret_12m"] == pytest.approx(359 / 107 - 1)
    assert fn.returns(closes[:100])["ret_6m"] is None


def test_eps_growth_and_peg_guardrail():
    g = fn.eps_growth_3y({"a": 1.0, "b": 1.2, "c": 1.5, "d": 2.0})
    assert g == pytest.approx(2 ** (1 / 3) - 1)
    short = pd.DataFrame([
        dict(ticker="CHEAP", score_quality=80, score_growth=80, price=50, ret_6m=.1, ret_12m=.2, eps=2.0, eps_g3=.25),   # P/E 25, PEG 1.0
        dict(ticker="PRICEY", score_quality=90, score_growth=90, price=300, ret_6m=.3, ret_12m=.5, eps=2.0, eps_g3=.25),  # P/E 150, PEG 6
        dict(ticker="LOSS", score_quality=50, score_growth=50, price=10, ret_6m=0, ret_12m=0, eps=-1.0, eps_g3=None),
    ])
    out = fn.rank(short, W, 2.0).set_index("ticker")
    assert out.loc["CHEAP", "passes_guardrail"] and not out.loc["PRICEY", "passes_guardrail"]
    assert "PEG 6.0" in out.loc["PRICEY", "guardrail_reason"]
    assert not out.loc["LOSS", "passes_guardrail"]


def test_fallback_after_three_blocked_months():
    assert fn.fallback_due([True, False, False, False], 3)
    assert not fn.fallback_due([False, False, True], 3)
    assert not fn.fallback_due([False, False], 3)
