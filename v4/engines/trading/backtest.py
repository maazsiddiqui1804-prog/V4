"""Trading Engine backtest (D-041–D-048, D-104). RESULTS ARE HISTORICAL SIMULATION, NEVER LIVE.

Plain English — day by day:
1. Morning: exits decided last night fill at the open; entries from last night's signals fill at
   the open (+ slippage). If the open is already below the stop, the entry is skipped.
2. During the day: if a stock opens below its stop, it's sold at the open (gap, D-047);
   if the low touches the stop, it's sold at the stop; if the high reaches entry + 2R,
   half is sold there (D-045).
3. Evening (close): after the half is off, the rest exits next morning if the close is below its
   20-day average (trail, PLACEHOLDER); any position held 20 trading days exits next morning.
   New signals are queued for tomorrow, best relative strength first, within
   max 6 open and 3 per sector (D-046). Risk 1% of current equity per trade, 0.5% in a weak market.
4. Drawdown brake (D-104): equity >15% below its peak → no new entries until the next quarter starts.
Every fill pays Zerodha delivery costs (costs.py) and slippage. R = net profit ÷ money at risk.
Known biases (shown in every report): today's Nifty 500 list applied to the past (survivorship),
no results-date blackout or surveillance-list exclusion (data not available historically).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from v4.engines.trading import costs, signals as sg


@dataclass
class Pos:
    symbol: str
    sector: str
    entry_date: object
    entry: float
    stop: float
    qty: int
    weak: bool
    left: int = 0
    partial: bool = False
    held: int = 0
    exit_next: str = ""
    pnl: float = 0.0
    legs: list = field(default_factory=list)

    def __post_init__(self):
        self.left = self.qty
        self.risk_amt = self.qty * (self.entry - self.stop)


def _quarter_start(d) -> tuple:
    return (d.year, (d.month - 1) // 3)


def run(px: pd.DataFrame, index_close: pd.Series, sectors: dict, cfg: dict, trade_from=None) -> dict:
    """trade_from: first date new entries may be signalled (earlier data only warms up the averages).
    The paper ledger replays this same engine from the paper start date, so paper and backtest
    can never disagree on the rules."""
    ind = sg.indicators(px, cfg)
    sig = sg.signals(ind, cfg)
    sig_by_day = {d: g for d, g in sig.groupby("date")}
    bars = {d: g.set_index("symbol") for d, g in ind.groupby("date")}
    weak = sg.weak_market(index_close).reindex(sorted(bars)).ffill().fillna(False)
    slip = cfg["slippage"]

    cash = float(cfg["capital_inr"])
    open_pos: list[Pos] = []
    pending: list[dict] = []
    trades, curve = [], []
    peak, paused_q = cash, None

    def sell(p: Pos, qty: int, price: float, day, why: str):
        nonlocal cash
        value = qty * price
        c = costs.sell_cost(value)
        cash += value - c
        p.pnl += value - c
        p.left -= qty
        p.legs.append((str(day)[:10], why, qty, round(price, 2)))

    for day in sorted(bars):
        b = bars[day]
        # 1. morning exits
        for p in list(open_pos):
            if p.exit_next and p.symbol in b.index:
                sell(p, p.left, b.at[p.symbol, "open"] * (1 - slip), day, p.exit_next)
        # 1b. morning entries
        for e in pending:
            if e["symbol"] not in b.index:
                continue
            o = b.at[e["symbol"], "open"] * (1 + slip)
            if o <= e["stop"]:
                continue
            risk_pct = cfg["weak_market_risk"] if e["weak"] else cfg["risk_per_trade"]
            equity = cash + sum(q.left * bars[day].at[q.symbol, "open"] for q in open_pos
                                if q.left and q.symbol in b.index)
            qty = math.floor(equity * risk_pct / (o - e["stop"]))
            qty = min(qty, math.floor(cash / (o * 1.0015)))
            if qty < 1:
                continue
            cost = costs.buy_cost(qty * o)
            cash -= qty * o + cost
            p = Pos(e["symbol"], e["sector"], day, o, e["stop"], qty, e["weak"])
            p.pnl -= qty * o + cost
            p.legs.append((str(day)[:10], "entry", qty, round(o, 2)))
            open_pos.append(p)
        pending = []
        # 2. intraday stop / partial
        for p in open_pos:
            if not p.left or p.symbol not in b.index:
                continue
            bar = b.loc[p.symbol]
            if bar["open"] <= p.stop:
                sell(p, p.left, bar["open"] * (1 - slip), day, "gap below stop")
                continue
            if bar["low"] <= p.stop:
                sell(p, p.left, p.stop * (1 - slip), day, "stop")
                continue
            target = p.entry + cfg["partial_at_r"] * (p.entry - p.stop)
            if not p.partial and bar["high"] >= target:
                q = math.floor(p.qty * cfg["partial_fraction"])
                if q >= 1:
                    sell(p, q, target * (1 - slip), day, "half at 2R")
                p.partial = True
        # 3. evening
        for p in open_pos:
            if not p.left or p.symbol not in b.index:
                continue
            p.held += 1
            bar = b.loc[p.symbol]
            if p.partial and bar["close"] < bar["dma20"]:
                p.exit_next = "trail: close below 20-day avg"
            elif p.held >= cfg["time_stop_days"]:
                p.exit_next = "time stop"
        for p in [p for p in open_pos if not p.left]:
            trades.append({"symbol": p.symbol, "sector": p.sector, "entry_date": str(p.entry_date)[:10],
                           "exit_date": p.legs[-1][0], "entry": round(p.entry, 2), "stop": round(p.stop, 2),
                           "qty": p.qty, "net_pnl": round(p.pnl, 2), "r": p.pnl / p.risk_amt,
                           "weak_market": p.weak, "exit_reason": p.legs[-1][1], "days": p.held})
        open_pos = [p for p in open_pos if p.left]
        equity = cash + sum(p.left * b.at[p.symbol, "close"] for p in open_pos if p.symbol in b.index)
        curve.append((day, equity))
        peak = max(peak, equity)
        if paused_q is None and equity < peak * (1 - cfg["drawdown_brake_pct"] / 100):
            paused_q = _quarter_start(day)
        if paused_q is not None and _quarter_start(day) != paused_q:
            paused_q, peak = None, equity          # resume at the next quarter (D-104)
        if paused_q is not None or day not in sig_by_day or (trade_from is not None and day < pd.Timestamp(trade_from)):
            continue
        held = {p.symbol for p in open_pos}
        per_sector: dict = {}
        for p in open_pos:
            per_sector[p.sector] = per_sector.get(p.sector, 0) + 1
        slots = cfg["max_open"] - len(open_pos)
        for r in sig_by_day[day].itertuples():
            if slots <= 0:
                break
            sec = sectors.get(r.symbol, "Unknown")
            if r.symbol in held or per_sector.get(sec, 0) >= cfg["max_per_sector"]:
                continue
            pending.append({"symbol": r.symbol, "sector": sec, "stop": r.stop, "weak": bool(weak.get(day, False))})
            per_sector[sec] = per_sector.get(sec, 0) + 1
            slots -= 1

    return {"trades": pd.DataFrame(trades), "curve": pd.Series(dict(curve)).sort_index(),
            "open_at_end": len(open_pos), "open": open_pos, "pending": pending,
            "paused": paused_q is not None}


def summary(res: dict, capital: float) -> dict:
    t, c = res["trades"], res["curve"]
    if t.empty:
        return {"trades": 0}
    years = max((c.index[-1] - c.index[0]).days / 365.25, 1e-9)
    dd = (c / c.cummax() - 1).min()
    s = {"trades": len(t), "avg_r": t["r"].mean(), "median_r": t["r"].median(),
         "win_rate": (t["r"] > 0).mean(), "total_return": c.iloc[-1] / capital - 1,
         "cagr": (c.iloc[-1] / capital) ** (1 / years) - 1, "max_drawdown": dd,
         "avg_days": t["days"].mean(),
         "weak_trades": int(t["weak_market"].sum()),
         "weak_avg_r": t.loc[t["weak_market"], "r"].mean() if t["weak_market"].any() else None}
    s["gate_d048"] = bool(s["trades"] >= 30 and s["avg_r"] >= 0.3)
    return s
