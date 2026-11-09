"""Checks the investment score on hand-made survivors."""
import math
import pandas as pd
import pytest

from v4.engines.investment import score as sc

W = {"quality": 40, "growth": 30, "momentum": 30}


def stock(sym, roce=(20, 20, 20), cfo=(90, 90), np_=(100, 100), sales=(15, 15), profit=(15, 15), mom=(10, 10)):
    return dict(security_id=hash(sym) % 10**6, symbol=sym,
                average_return_on_capital_employed_3years=roce[0],
                average_return_on_capital_employed_5years=roce[1],
                average_return_on_capital_employed_10years=roce[2],
                cash_from_operations_last_year=cfo[0], cash_from_operations_preceding_year=cfo[1],
                net_profit_last_year=np_[0], net_profit_preceding_year=np_[1],
                sales_growth_3years=sales[0], sales_growth_5years=sales[1],
                profit_growth_3years=profit[0], profit_growth_5years=profit[1],
                return_over_6months=mom[0], return_over_1year=mom[1])


def test_consistency_beats_one_great_stretch():
    steady = stock("STEADY", roce=(25, 25, 25))
    spiky = stock("SPIKY", roce=(60, 30, 8))      # great lately, weak decade
    out = sc.score(pd.DataFrame([steady, spiky]), W).set_index("symbol")
    assert out.loc["STEADY", "score_quality"] > out.loc["SPIKY", "score_quality"]


def test_young_company_needs_two_roce_periods():
    young = stock("YOUNG", roce=(40, math.nan, math.nan))
    out = sc.score(pd.DataFrame([young, stock("OLD")]), W).set_index("symbol")
    assert math.isnan(out.loc["YOUNG", "roce_floor"])


def test_steady_growth_beats_one_hot_period():
    out = sc.score(pd.DataFrame([stock("STEADY", sales=(18, 18)), stock("HOT", sales=(40, 5))]), W).set_index("symbol")
    assert out.loc["STEADY", "score_growth"] > out.loc["HOT", "score_growth"]


def test_weights_change_ranking():
    q = stock("QUALITY", roce=(40, 40, 40), mom=(-5, -5))
    m = stock("MOMENTUM", roce=(15, 15, 15), mom=(60, 80))
    df = pd.DataFrame([q, m])
    normal = sc.score(df, {"quality": 40, "growth": 30, "momentum": 30})
    weak = sc.score(df, {"quality": 55, "growth": 30, "momentum": 15})
    # Worked by hand: normal 72.5 (QUALITY) vs 77.5 (MOMENTUM); weak 78.1 vs 71.9
    assert normal.symbol.tolist() == ["MOMENTUM", "QUALITY"]
    assert weak.symbol.tolist() == ["QUALITY", "MOMENTUM"]
    assert normal.score_total.iloc[0] == pytest.approx(77.5)


def test_ranks_are_0_to_100_and_ordered():
    df = pd.DataFrame([stock(f"S{i}", roce=(10 + i,) * 3, mom=(i, i)) for i in range(10)])
    out = sc.score(df, W)
    assert out.score_total.between(0, 100).all()
    assert out["rank"].tolist() == list(range(1, 11))
    assert out.symbol.iloc[0] == "S9"


def test_regime_without_history_is_cautious(tmp_path):
    from v4.db import init_db
    init_db(tmp_path / "t.sqlite")
    state, note = sc.regime(tmp_path / "t.sqlite")
    assert state == "weak" and "unavailable" in note
