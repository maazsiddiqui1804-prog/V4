"""Checks the monthly buy plan."""
import pandas as pd
import pytest

from v4.engines.investment import portfolio as pf

RULES = {"target_holdings": 15, "min_buy_inr": 10000, "max_names_per_month": 5, "max_rank": 100,
         "max_per_sector_while_filling": 3, "pct_caps_from_holdings": 10,
         "stock_cap": 0.10, "sector_cap": 0.25}
EMPTY = pd.DataFrame(columns=["security_id", "symbol", "quantity", "current_price", "sector"])


def ranked(rows):
    return pd.DataFrame([dict(rank=i + 1, symbol=s, security_id=i + 1, sector=sec, current_price=p,
                              buy_below=p * 1.1, passes_guardrail=ok)
                         for i, (s, sec, p, ok) in enumerate(rows)])


def test_month_one_buys_two_best_passing_names():
    r = ranked([("A", "IT", 500, False), ("B", "IT", 400, True), ("C", "Auto", 1000, True), ("D", "Auto", 200, True)])
    plan = pf.plan_buys(r, EMPTY, 25000, RULES)
    assert [o.symbol for o in plan.orders] == ["B", "C"]          # A fails guardrail
    assert plan.orders[0].shares == 31 and plan.orders[1].shares == 12   # floor(12500/400), floor(12500/1000)
    assert plan.orders[0].limit == pytest.approx(440)
    assert plan.leftover == pytest.approx(25000 - 31 * 400 - 12 * 1000)


def test_below_minimum_keeps_cash():
    plan = pf.plan_buys(ranked([("A", "IT", 100, True)]), EMPTY, 9000, RULES)
    assert not plan.orders and plan.leftover == 9000


def test_expensive_share_skipped():
    r = ranked([("MRF", "Auto", 150000, True), ("B", "IT", 400, True), ("C", "FMCG", 300, True)])
    plan = pf.plan_buys(r, EMPTY, 25000, RULES)
    assert [o.symbol for o in plan.orders] == ["B", "C"]
    assert any("MRF" in n and "costs more" in n for n in plan.notes)


def test_sector_limit_while_filling():
    holdings = pd.DataFrame([dict(security_id=100 + i, symbol=f"H{i}", quantity=10, current_price=1000, sector="IT")
                             for i in range(3)])
    r = ranked([("B", "IT", 400, True), ("C", "FMCG", 300, True), ("D", "Auto", 200, True)])
    plan = pf.plan_buys(r, holdings, 25000, RULES)
    assert [o.symbol for o in plan.orders] == ["C", "D"]
    assert any("already 3 holdings in IT" in n for n in plan.notes)


def test_walks_past_top_20_but_not_past_100():
    rows = [(f"X{i}", "IT", 100, False) for i in range(20)] + [("DEEP", "FMCG", 100, True)]
    plan = pf.plan_buys(ranked(rows), EMPTY, 25000, RULES)
    assert [o.symbol for o in plan.orders] == ["DEEP"]
    assert any("rank 21" in n for n in plan.notes)
    rows = [(f"X{i}", "IT", 100, False) for i in range(100)] + [("TOO_DEEP", "FMCG", 100, True)]
    plan = pf.plan_buys(ranked(rows), EMPTY, 25000, RULES)
    assert not plan.orders and plan.leftover == 25000


def test_full_portfolio_tops_up_most_underweight():
    holdings = pd.DataFrame([dict(security_id=i + 1, symbol=f"S{i}", quantity=q, current_price=100, sector=f"Sec{i}")
                             for i, q in enumerate([100] * 13 + [10, 40])])   # S13 most underweight
    r = ranked([(f"S{i}", f"Sec{i}", 100, True) for i in range(15)])
    plan = pf.plan_buys(r, holdings, 25000, RULES)
    assert plan.orders[0].symbol == "S13" and all(o.kind == "top-up" for o in plan.orders)


def test_blocked_names_never_bought():
    r = ranked([("FLAG", "IT", 400, True), ("B", "Auto", 400, True), ("C", "FMCG", 300, True)])
    plan = pf.plan_buys(r, EMPTY, 25000, RULES, blocked_ids={1})
    assert [o.symbol for o in plan.orders] == ["B", "C"]


def test_every_order_clears_minimum_after_rounding():
    # Rs 50k over five Rs 3,545-ish shares would round below Rs 10k; must not happen
    r = ranked([(f"P{i}", f"Sec{i}", p, True) for i, p in enumerate([3545, 427, 2181, 162, 3883, 255])])
    plan = pf.plan_buys(r, EMPTY, 50000, RULES)
    assert plan.orders and all(o.amount >= 10000 for o in plan.orders)
    assert sum(o.amount for o in plan.orders) <= 50000
