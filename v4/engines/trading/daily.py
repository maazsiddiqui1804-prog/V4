"""Trading Engine evening plan (D-043, D-044, D-045, D-046, D-097). Same rules as the backtest.

Plain English — run after the close (~6:30 PM) on today's end-of-day prices:
- NEW: stocks that broke out today → buy at tomorrow's open, with stop, 2R target and quantity
  (1% of trading capital at risk, 0.5% in a weak market), within 6 open / 3 per sector.
- WATCH: stocks in an uptrend and in the top 20% for strength, within 3% of breaking out →
  trigger price for a Kite price alert (D-097).
- OPEN POSITIONS: what to do tomorrow — exit (stop hit, trail, time stop), sell half at 2R, or hold.
Paper first (D-047). The system never places orders (D-003); Maaz acts, and places each stop as a GTT (D-110).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from v4.engines.trading import signals as sg


@dataclass
class Open:
    symbol: str
    sector: str
    entry: float
    stop: float
    qty: int
    left: int
    partial: bool
    held: int          # trading days held so far


def evening_plan(px: pd.DataFrame, index_close: pd.Series, sectors: dict, positions: list[Open],
                 equity: float, cfg: dict, near: float = 0.03) -> dict:
    ind = sg.indicators(px, cfg)
    day = ind["date"].max()
    today = ind[ind["date"] == day].set_index("symbol")
    weak = bool(sg.weak_market(index_close).iloc[-1])
    risk = cfg["weak_market_risk"] if weak else cfg["risk_per_trade"]

    actions = []
    for p in positions:
        if p.symbol not in today.index:
            actions.append((p.symbol, "CHECK", "no price today"))
            continue
        b = today.loc[p.symbol]
        target = p.entry + cfg["partial_at_r"] * (p.entry - p.stop)
        if b["close"] <= p.stop:
            actions.append((p.symbol, "EXIT", f"closed at/below stop ₹{p.stop:,.2f} — GTT should have fired"))
        elif p.partial and b["close"] < b["dma20"]:
            actions.append((p.symbol, "EXIT", f"trail: close below 20-day average ₹{b['dma20']:,.2f}"))
        elif p.held + 1 >= cfg["time_stop_days"]:
            actions.append((p.symbol, "EXIT", f"time stop ({cfg['time_stop_days']} trading days)"))
        elif not p.partial:
            actions.append((p.symbol, "HOLD", f"sell half at ₹{target:,.2f} (2R); stop ₹{p.stop:,.2f}"))
        else:
            actions.append((p.symbol, "HOLD", f"trail: exit if a close is below its 20-day average; stop ₹{p.stop:,.2f}"))

    exiting = {s for s, a, _ in actions if a == "EXIT"}
    staying = [p for p in positions if p.symbol not in exiting]
    per_sector: dict = {}
    for p in staying:
        per_sector[p.sector] = per_sector.get(p.sector, 0) + 1
    slots = cfg["max_open"] - len(staying)
    held = {p.symbol for p in positions}

    new, skipped = [], []
    sig = sg.signals(ind[ind["date"] == day], cfg)
    for r in sig.itertuples():
        sec = sectors.get(r.symbol, "Unknown")
        why = ("already held" if r.symbol in held else "6 positions open" if slots <= 0
               else f"3 already in {sec}" if per_sector.get(sec, 0) >= cfg["max_per_sector"] else "")
        if why:
            skipped.append((r.symbol, why))
            continue
        per_share = r.close - r.stop
        qty = math.floor(equity * risk / per_share)
        if qty < 1:
            skipped.append((r.symbol, "position too small"))
            continue
        new.append({"symbol": r.symbol, "sector": sec, "ref_close": round(r.close, 2), "stop": round(r.stop, 2),
                    "target_2r": round(r.close + cfg["partial_at_r"] * per_share, 2), "qty": qty,
                    "risk_inr": round(qty * per_share)})
        per_sector[sec] = per_sector.get(sec, 0) + 1
        slots -= 1

    t = today
    setup = ((t["value20_cr"] >= cfg["liquidity_floor_cr_per_day"]) & (t["dma_fast"] > t["dma_slow"])
             & (t["close"] > t["dma_fast"]) & (t["rs_pct"] >= 1 - cfg["rs_top_fraction"]))
    trig = t["prior_high_close"].combine(t["close"], max)          # tomorrow must close above today's 20-day high
    close_to = (trig / t["close"] - 1).between(0, near, inclusive="right")
    watch = t[setup & close_to & ~t.index.isin(held) & ~t.index.isin([n["symbol"] for n in new])]
    watchlist = [{"symbol": s, "trigger": round(float(trig[s]), 2)} for s in watch.sort_values("rs_pct", ascending=False).index]

    return {"date": str(day)[:10], "weak_market": weak, "new": new, "skipped": skipped,
            "actions": actions, "watchlist": watchlist}


def render(plan: dict, mode: str = "PAPER") -> str:
    L = [f"📈 V4 trading — {plan['date']} · {mode}" + (" · weak market: half size" if plan["weak_market"] else "")]
    L.append("\nOPEN POSITIONS (act at tomorrow's open):")
    L += [f"{a} {s} — {why}" for s, a, why in plan["actions"]] or ["— none"]
    L.append("\nNEW (buy at tomorrow's open; place the stop as a GTT immediately):")
    L += [f"{n['symbol']} — {n['qty']} shares, stop ₹{n['stop']:,.2f}, 2R ₹{n['target_2r']:,.2f}, "
          f"risk ≈ ₹{n['risk_inr']:,} (ref close ₹{n['ref_close']:,.2f})" for n in plan["new"]] or ["— none"]
    if plan["skipped"]:
        L.append("Skipped: " + ", ".join(f"{s} ({w})" for s, w in plan["skipped"][:8]))
    L.append("\nWATCH (set Kite price alerts; a close above the trigger on volume = signal):")
    L += [f"{w['symbol']} ≥ ₹{w['trigger']:,.2f}" for w in plan["watchlist"][:10]] or ["— none"]
    L.append("\nV4 never places orders. Starting numbers are untested placeholders.")
    return "\n".join(L)
