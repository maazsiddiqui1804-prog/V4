"""Paper trading ledger (D-047, D-048). Paper results are SIMULATED, never live (CLAUDE.md rule 4).

Plain English: every evening the paper ledger replays the exact backtest engine from the paper
start date on real end-of-day prices. So paper trades follow the rules mechanically, with full
costs, slippage and gap fills, and can't drift from the backtest. Output: closed paper trades,
open paper positions (fed into the evening plan), and progress against the go-live bar
(D-048: ≥3 months AND ≥30 trades AND ≥0.3R average after costs).
"""
from __future__ import annotations

import pandas as pd

from v4.engines.trading import backtest as bt, daily


def replay(px: pd.DataFrame, index_close: pd.Series, sectors: dict, cfg: dict, start: str) -> dict:
    res = bt.run(px, index_close, sectors, cfg, trade_from=start)
    positions = [daily.Open(p.symbol, p.sector, p.entry, p.stop, p.qty, p.left, p.partial, p.held)
                 for p in res["open"]]
    t = res["trades"]
    curve = res["curve"][res["curve"].index >= pd.Timestamp(start)]
    equity = float(curve.iloc[-1]) if len(curve) else float(cfg["capital_inr"])
    return {"trades": t, "positions": positions, "equity": equity, "paused": res["paused"],
            "gate": gate(t, start, curve.index[-1] if len(curve) else pd.Timestamp(start))}


def gate(trades: pd.DataFrame, start: str, today) -> dict:
    months = (pd.Timestamp(today) - pd.Timestamp(start)).days / 30.44
    n = len(trades)
    avg = float(trades["r"].mean()) if n else None
    return {"months": round(months, 1), "trades": n, "avg_r": avg,
            "met": bool(months >= 3 and n >= 30 and avg is not None and avg >= 0.3)}


def gate_line(g: dict) -> str:
    avg = f"{g['avg_r']:.2f}R" if g["avg_r"] is not None else "—"
    return (f"Paper go-live bar (D-048): {g['months']}/3 months · {g['trades']}/30 trades · avg {avg}/0.30R → "
            f"{'MET' if g['met'] else 'not yet'} (simulated results, not live)")
