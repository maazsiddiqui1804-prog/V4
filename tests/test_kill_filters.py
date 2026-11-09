"""Checks each kill filter on hand-made stocks, one failure at a time."""
import math
import pandas as pd
import pytest

from v4.engines.investment import filters as kf

RULES = {"max_debt_equity": 1.5, "min_interest_cover": 3.0, "near_zero_debt": 0.1,
         "max_promoter_pledge_pct": 10, "min_cash_conversion": 0.7, "blank_means_fail": True}
GOOD = dict(security_id=1, symbol="GOOD", net_profit_last_year=100, net_profit_preceding_year=90,
            net_profit=110, debt_to_equity=0.5, interest_coverage_ratio=8, pledged_percentage=0,
            cash_from_operations_last_year=95, cash_from_operations_preceding_year=85)


def one(**changes):
    row = dict(GOOD, **changes)
    res = kf.apply(pd.DataFrame([row]), RULES).iloc[0]
    return res.passed, " | ".join(res.reasons)


def test_good_stock_passes():
    assert one() == (True, "")


@pytest.mark.parametrize("changes,expect", [
    (dict(net_profit=-5), "loss"),
    (dict(net_profit_preceding_year=-1), "loss"),
    (dict(debt_to_equity=1.6), "debt-to-equity 1.60"),
    (dict(interest_coverage_ratio=2.9), "interest cover 2.9"),
    (dict(pledged_percentage=10.5), "pledge 10.5"),
    (dict(cash_from_operations_last_year=40, cash_from_operations_preceding_year=60), "cash conversion 0.53"),
])
def test_each_filter_knocks_out(changes, expect):
    passed, why = one(**changes)
    assert not passed and expect in why


def test_boundaries_pass():
    # exactly at the limit is allowed
    assert one(debt_to_equity=1.5, interest_coverage_ratio=3.0, pledged_percentage=10)[0]


def test_low_debt_skips_interest_cover():
    assert one(debt_to_equity=0.05, interest_coverage_ratio=math.nan)[0]
    assert one(debt_to_equity=0.05, interest_coverage_ratio=1.0)[0]


def test_blank_is_fail():
    passed, why = one(cash_from_operations_preceding_year=math.nan)
    assert not passed and "missing" in why
    passed, why = one(debt_to_equity=math.nan)
    assert not passed and "debt-to-equity missing" in why


def test_run_saves_reasons(tmp_path):
    from tests.test_screener_import import run as import_sample
    from v4.db import connect
    import_sample(tmp_path)   # GOOD Co (passes basics but lacks columns) etc.
    res = kf.run("2026-11-09", tmp_path / "t.sqlite", RULES)
    assert len(res) >= 1
    with connect(tmp_path / "t.sqlite") as c:
        saved = c.execute("SELECT COUNT(*), SUM(passed) FROM kill_filter_results").fetchone()
    assert saved[0] == len(res) and saved[1] == 0      # sample lacks cash-flow columns → blank = fail
