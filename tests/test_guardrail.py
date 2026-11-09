"""Checks the India buy-below price and PEG check."""
import math
import pandas as pd
import pytest

from v4.engines.investment import guardrail as g

RULES = {"india_pe_basis": "historical_pe_10years", "india_pe_margin": 0.20, "india_max_peg": 2.0}


def one(**kw):
    row = dict(symbol="X", current_price=100.0, price_to_earning=20.0,
               historical_pe_10years=25.0, historical_pe_5years=30.0, peg_ratio=1.5)
    row.update(kw)
    return g.apply(pd.DataFrame([row]), RULES).iloc[0]


def test_buy_below_formula():
    r = one()
    assert r.buy_below == pytest.approx(100 * 25 * 1.2 / 20)   # 150
    assert r.passes_guardrail


def test_expensive_vs_own_history_fails():
    r = one(price_to_earning=40.0)                             # buy-below 75 < price 100
    assert not r.passes_guardrail and "above buy-below" in r.guardrail_reason


def test_peg_cap_and_blank():
    assert not one(peg_ratio=2.1).passes_guardrail
    assert one(peg_ratio=2.0).passes_guardrail
    assert "PEG missing" in one(peg_ratio=math.nan).guardrail_reason
    assert not one(peg_ratio=-0.5).passes_guardrail


def test_falls_back_to_5y_history():
    r = one(historical_pe_10years=math.nan)
    assert r.buy_below == pytest.approx(100 * 30 * 1.2 / 20)


def test_loss_making_pe_has_no_buy_below():
    r = one(price_to_earning=-5.0)
    assert math.isnan(r.buy_below) and not r.passes_guardrail
