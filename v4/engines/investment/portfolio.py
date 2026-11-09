"""Investment Engine, step 4: turn the ranked list into this month's buy orders (D-028, D-060, D-092, D-105, D-126).

Plain English:
- Monthly amount: a standing default (₹25,000) unless overridden for that month.
- While V4 holds fewer than 15 India stocks: buy NEW names, best rank first.
  Once it holds 15: top up the most underweight holdings that still qualify.
- A name qualifies if it passes the kill filters and the guardrail and ranks in the
  top 100 (anything lower would be sold next month under D-027). Top 20 first;
  if not enough pass, walk further down the ranking (D-126).
- 2–5 names a month, at least ₹10,000 each (D-105). The amount is split equally.
  A stock whose single share costs more than its slice is skipped.
- Concentration while filling (D-126): at most 3 holdings per sector. The 10% stock
  / 25% sector caps (D-060) apply once V4 holds 10+ stocks.
- Quantity = whole shares at today's price; limit price = the buy-below price.
- Anything left over waits in the liquid fund (D-029).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Order:
    symbol: str
    amount: float
    shares: int
    limit: float
    rank: int
    kind: str          # 'new' or 'top-up'


@dataclass
class Plan:
    amount: float
    orders: list = field(default_factory=list)
    leftover: float = 0.0
    notes: list = field(default_factory=list)


def plan_buys(ranked: pd.DataFrame, holdings: pd.DataFrame, amount: float, rules: dict,
              blocked_ids: set | None = None) -> Plan:
    """ranked: rank, symbol, security_id, sector, current_price, buy_below, passes_guardrail.
    holdings: security_id, symbol, quantity, current_price, sector (V4 India holdings)."""
    target_n = rules["target_holdings"]          # 15 (D-028)
    min_buy = rules["min_buy_inr"]               # 10,000 (D-105)
    max_names = rules["max_names_per_month"]     # 5 (D-105)
    pool_floor = rules["max_rank"]               # 100 (D-027)
    sector_max = rules["max_per_sector_while_filling"]   # 3 (D-126)
    caps_from = rules["pct_caps_from_holdings"]  # 10 (D-126)
    stock_cap, sector_cap = rules["stock_cap"], rules["sector_cap"]   # 10%, 25% (D-060)

    plan = Plan(amount=amount)
    held = set(holdings["security_id"]) if len(holdings) else set()
    hv = holdings.assign(value=holdings["quantity"] * holdings["current_price"]) if len(holdings) else \
        pd.DataFrame(columns=["security_id", "symbol", "sector", "value"])
    total_after = float(hv["value"].sum()) + amount
    n_slots = min(max_names, int(amount // min_buy))
    if n_slots < 1:
        plan.leftover = amount
        plan.notes.append(f"₹{amount:,.0f} is below the ₹{min_buy:,.0f} minimum per buy — kept in the liquid fund")
        return plan

    eligible = ranked[(ranked["rank"] <= pool_floor) & ranked["passes_guardrail"]].sort_values("rank")
    if blocked_ids:   # red-flagged (D-061) or being sold this month: never buy
        eligible = eligible[~eligible["security_id"].isin(blocked_ids)]
    sector_count = hv.groupby("sector").size().to_dict() if len(hv) else {}
    sector_value = hv.groupby("sector")["value"].sum().to_dict() if len(hv) else {}
    pct_caps_on = len(held) >= caps_from

    if len(held) < target_n:
        kind = "new"
        n_slots = min(n_slots, target_n - len(held))
        candidates = eligible[~eligible["security_id"].isin(held)]
    else:
        kind = "top-up"
        target_value = total_after / target_n
        under = hv.assign(gap=target_value - hv["value"])
        under = under[under["gap"] > 0]   # any shortfall; the buy itself is still ≥ min_buy
        candidates = eligible[eligible["security_id"].isin(under["security_id"])].merge(
            under[["security_id", "gap"]], on="security_id").sort_values("gap", ascending=False)

    slice_ = amount / n_slots
    chosen = []
    for r in candidates.itertuples():
        if len(chosen) == n_slots:
            break
        sector = getattr(r, "sector", None) or "Unknown"
        if kind == "new" and not pct_caps_on and sector_count.get(sector, 0) >= sector_max:
            plan.notes.append(f"{r.symbol} skipped: already {sector_max} holdings in {sector}")
            continue
        if pct_caps_on:
            if slice_ / total_after > stock_cap:
                plan.notes.append(f"{r.symbol} skipped: would exceed the {stock_cap:.0%} stock cap")
                continue
            if (sector_value.get(sector, 0) + slice_) / total_after > sector_cap:
                plan.notes.append(f"{r.symbol} skipped: {sector} would exceed the {sector_cap:.0%} sector cap")
                continue
        if r.current_price > slice_:
            plan.notes.append(f"{r.symbol} skipped: one share (₹{r.current_price:,.0f}) costs more than its ₹{slice_:,.0f} slice")
            continue
        chosen.append(r)
        sector_count[sector] = sector_count.get(sector, 0) + 1
        sector_value[sector] = sector_value.get(sector, 0) + slice_
        if r.rank > 20:
            plan.notes.append(f"{r.symbol} is rank {r.rank}: not enough top-20 names passed this month")

    if not chosen:
        plan.leftover = amount
        plan.notes.append("No qualifying name this month — the whole amount waits in the liquid fund (D-029)")
        return plan

    slice_ = amount / len(chosen) if amount / len(chosen) >= min_buy else slice_
    spent = 0.0
    for r in chosen:
        shares = int(math.floor(slice_ / r.current_price))
        cost = shares * r.current_price
        spent += cost
        plan.orders.append(Order(r.symbol, round(cost, 2), shares, float(r.buy_below), int(r.rank), kind))
    plan.leftover = round(amount - spent, 2)
    if len(chosen) < n_slots:
        plan.notes.append(f"Only {len(chosen)} of {n_slots} slots filled")
    return plan


def holdings_frame(as_of: str, db_path) -> pd.DataFrame:
    """Latest holdings snapshot on or before as_of, with today's price and sector."""
    from v4.db import connect
    with connect(db_path) as c:
        snap = c.execute("SELECT MAX(snapshot_date) FROM holdings_snapshots WHERE snapshot_date<=? AND engine='investment'",
                         (as_of,)).fetchone()[0]
        if snap is None:
            return pd.DataFrame(columns=["security_id", "symbol", "quantity", "current_price", "sector"])
        return pd.read_sql(
            """SELECT h.security_id, s.symbol, h.quantity, s.sector,
                      COALESCE((SELECT value FROM fundamentals f WHERE f.security_id=h.security_id
                                AND f.metric='current_price' AND f.as_of<=? ORDER BY f.as_of DESC LIMIT 1),
                               h.avg_price) AS current_price
               FROM holdings_snapshots h JOIN securities s USING(security_id)
               WHERE h.snapshot_date=? AND h.engine='investment'""", c, params=(as_of, snap))


def with_sector(ranked: pd.DataFrame, db_path) -> pd.DataFrame:
    from v4.db import connect
    with connect(db_path) as c:
        sec = pd.read_sql("SELECT security_id, sector FROM securities", c)
    return ranked.drop(columns=[c for c in ["sector"] if c in ranked]).merge(sec, on="security_id", how="left")
