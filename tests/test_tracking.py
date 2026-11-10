"""Forward-tracking of frozen lists (D-063)."""
import numpy as np
import pandas as pd
import pytest
from v4.engines.investment import tracking as tr

D = pd.bdate_range("2026-12-01", periods=60)


def setup():
    lists = pd.DataFrame({"list_month": "2026-12", "symbol": [f"S{i}" for i in range(9)], "rank": range(1, 10),
                          "score_quality": [90, 80, 70, 60, 50, 40, 30, 20, 10], "score_growth": 50.0,
                          "score_momentum": 50.0, "score_total": [90, 80, 70, 60, 50, 40, 30, 20, 10],
                          "passes_guardrail": [1, 1, 1, 0, 0, 0, 1, 1, 1], "frozen_at": "2026-12-02T10:00:00+00:00"})
    rows = []
    for i in range(9):
        growth = 1 + (9 - i) * 0.01                        # higher quality → bigger gain
        rows += [{"date": d, "symbol": f"S{i}", "close": 100 * growth ** (k / 59)} for k, d in enumerate(D)]
    idx = pd.Series(np.linspace(100, 102, 60), index=D)
    return lists, pd.DataFrame(rows), idx


def test_returns_measured_from_freeze_date_vs_index():
    lists, px, idx = setup()
    t = tr.track(lists, px, idx)
    s0 = t[t.symbol == "S0"].iloc[0]
    p0 = px[(px.symbol == "S0") & (px.date == D[1])].close.iloc[0]
    assert s0["return"] == pytest.approx(px[px.symbol == "S0"].close.iloc[-1] / p0 - 1)
    assert s0["excess"] == pytest.approx(s0["return"] - (102 / idx.iloc[1] - 1))


def test_checks_point_the_right_way():
    lists, px, idx = setup()
    t = tr.track(lists, px, idx)
    f = tr.factor_check(t).set_index("Score part")
    assert f.loc["Quality", "Gap"] > 0
    rc = tr.ranking_check(t, top=3)
    assert rc["Ahead of index"].iloc[0] > 0
    g = tr.guardrail_check(t)
    assert set(g["Names"]) == {"Buyable (price under limit)", "Too expensive (skipped)"}


def test_empty_inputs_are_safe():
    assert tr.track(pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=float)).empty


def test_score_parts_without_spread_are_skipped():
    lists, px, idx = setup()
    f = tr.factor_check(tr.track(lists, px, idx))
    assert "Growth" not in set(f["Score part"]) and "Quality" in set(f["Score part"])
