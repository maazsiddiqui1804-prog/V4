"""Checks US kill filters and the quality+growth shortlist."""
import math
import pytest
from v4.engines.us import score as us

RULES = {"max_debt_equity": 1.5, "min_interest_cover": 3.0, "near_zero_debt": 0.1, "min_cash_conversion": 0.7}
W = {"quality": 40, "growth": 30}
Y = ["2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"]


def fin(rev=(100, 110, 121, 133), ni=(10, 11, 12, 13), cfo=(11, 12, 13), op=(15, 16, 17),
        assets=(100, 105, 110), cl=(20, 21, 22), equity=60, debt=10, interest=1):
    return {"revenue": dict(zip(Y, rev)), "net_income": dict(zip(Y, ni)), "cfo": dict(zip(Y[1:], cfo)),
            "operating_income": dict(zip(Y[1:], op)), "assets": dict(zip(Y[1:], assets)),
            "current_liabilities": dict(zip(Y[1:], cl)), "equity": {Y[-1]: equity},
            "debt_noncurrent": {Y[-1]: debt}, "debt_current": {}, "interest_expense": {Y[-1]: interest}}


def test_metrics_basic():
    m = us.metrics(fin())
    assert m["losses_3y"] is False
    assert m["debt_equity"] == pytest.approx(10 / 60)
    assert m["interest_cover"] == pytest.approx(17)
    assert m["cash_conversion_3y"] == pytest.approx(36 / 36)
    assert m["roce_floor_3y"] == pytest.approx(min(15 / 80, 16 / 84, 17 / 88))
    assert m["rev_growth"] == pytest.approx(min(133 / 121 - 1, (133 / 100) ** (1 / 3) - 1))


def test_loss_in_any_of_three_years_kills():
    m = us.metrics(fin(ni=(10, -1, 12, 13)))
    assert "loss in last 3 years" in us.kill(m, RULES)


def test_short_history_fails_not_passes():
    f = fin()
    f["net_income"] = {Y[-1]: 13}
    assert "profit history missing" in us.kill(us.metrics(f), RULES)


def test_debt_free_skips_interest_cover():
    m = us.metrics(fin(debt=0, interest=0))
    assert m["debt_equity"] == 0 and not us.kill(m, RULES)


def test_shortlist_ranks_and_cuts():
    rows = []
    for i in range(10):
        m = us.metrics(fin(op=(10 + i, 10 + i, 10 + i), rev=(100, 105, 110 + i, 116 + 2 * i)))
        rows.append({"ticker": f"T{i}", **m})
    bad = us.metrics(fin(ni=(10, -5, 12, 13)))
    rows.append({"ticker": "LOSS", **bad})
    s = us.shortlist(rows, RULES, W, size=4)
    assert "LOSS" not in s.ticker.tolist()
    assert s.shortlisted.sum() == 4 and s.ticker.iloc[0] == "T9"


def test_interest_paid_but_debt_not_found_fails():
    f = fin()
    f["debt_noncurrent"] = {}
    m = us.metrics(f)
    assert m["debt_equity"] is None and "debt-to-equity missing" in us.kill(m, RULES)


def test_stale_interest_figure_is_ignored():
    f = fin(debt=0)
    f["interest_expense"] = {"2021-12-31": 5}
    m = us.metrics(f)
    assert m["debt_equity"] == 0 and m["interest_cover"] is None and not us.kill(m, RULES)
