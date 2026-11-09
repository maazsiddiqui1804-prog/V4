"""Checks the verdict on each holding."""
import pandas as pd

from v4.engines.investment import sells as sl

RULES = {"target_holdings": 15, "max_rank": 100, "trim_above_x_target": 2.0, "trim_to_x_target": 2.0,
         "quality_bottom_fraction": 0.25}


def run(holdings, filters, ranked, prev=None, flags=()):
    v = sl.verdicts(pd.DataFrame(holdings), pd.DataFrame(filters), pd.DataFrame(ranked), prev or {}, set(flags), RULES)
    return {x.symbol: (x.action, x.shares, x.reason) for x in v}


def base(n=15, price=100, qty=10):
    holdings = [dict(security_id=i, symbol=f"S{i}", quantity=qty, current_price=price) for i in range(n)]
    filters = [dict(security_id=i, passed=True, reasons=[]) for i in range(n)]
    ranked = [dict(security_id=i, rank=i + 1, score_quality=50 + i) for i in range(n)]
    return holdings, filters, ranked


def test_all_fine_is_hold_except_bottom_quality_quarter():
    out = run(*base())
    sells = sorted(s for s, (a, _, _) in out.items() if a == "SELL")
    assert sells == ["S0", "S1", "S2"]                               # lowest 3 of 15 quality scores (≤25%)
    assert all(a == "HOLD" for s, (a, _, _) in out.items() if s not in sells)


def test_filter_failure_sells_everything():
    h, f, r = base()
    f[5] = dict(security_id=5, passed=False, reasons=["promoter pledge 12.0% > 10%"])
    out = run(h, f, r)
    assert out["S5"][0] == "SELL" and out["S5"][1] == 10 and "pledge" in out["S5"][2]


def test_bottom_quarter_quality_sells():
    h, f, r = base()
    out = run(h, f, r)
    assert out["S0"][0] == "SELL" and "quality" in out["S0"][2]      # lowest quality score
    assert out["S14"][0] == "HOLD"


def test_rank_below_100_needs_two_months():
    h, f, r = base(n=2)
    r = [dict(security_id=0, rank=150, score_quality=90), dict(security_id=1, rank=150, score_quality=95)]
    out = run(h, f, r, prev={0: 120, 1: 40})
    assert out["S0"][0] == "SELL"            # below 100 last month too
    assert out["S1"][0] == "WATCH"           # first month below


def test_red_flag_is_review_not_sell():
    h, f, r = base()
    out = run(h, f, r, flags={7})
    assert out["S7"][0] == "REVIEW"


def test_trim_back_to_two_x_target():
    h, f, r = base()
    h[10]["quantity"] = 60                    # 6,000 of 20,000 total; target 1,333; 2x = 2,667
    out = run(h, f, r)
    action, shares, _ = out["S10"]
    assert action == "TRIM"
    total = 14 * 1000 + 6000
    assert shares == int((6000 - 2 * total / 15) // 100)


def test_left_universe_sells():
    h, f, r = base(n=2)
    f = [f[0]]
    out = run(h, f, r)
    assert out["S1"][0] == "SELL" and "universe" in out["S1"][2]
