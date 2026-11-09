"""Run the Trading Engine backtest and report it. HISTORICAL SIMULATION — NOT LIVE RESULTS.

python -m v4.jobs.backtest   → data/backtest/trades.csv, summary.json, Telegram summary
"""
from __future__ import annotations

import json
import sys

import yaml

from v4 import alerts
from v4.db import ROOT
from v4.engines.trading import backtest as bt
from v4.importers import india_prices as ip

OUT = ROOT / "data" / "backtest"
BIASES = ("Biases: today's Nifty 500 list used for the past (flatters results); no results-date blackout "
          "or surveillance exclusion; Yahoo prices. Starting numbers are untested PLACEHOLDERS.")


def run() -> str:
    cfg = yaml.safe_load((ROOT / "config" / "placeholders.yaml").read_text())["trading"]
    px, idx = ip.load()
    sectors = dict(ip.universe().itertuples(index=False, name=None))
    res = bt.run(px, idx, sectors, cfg)
    s = bt.summary(res, cfg["capital_inr"])
    OUT.mkdir(parents=True, exist_ok=True)
    res["trades"].to_csv(OUT / "trades.csv", index=False)
    res["curve"].rename("equity").to_csv(OUT / "equity.csv")
    period = f"{res['curve'].index[0]:%b %Y}–{res['curve'].index[-1]:%b %Y}"
    (OUT / "summary.json").write_text(json.dumps({"period": period, **{k: (round(v, 4) if isinstance(v, float) else v)
                                                                       for k, v in s.items()}}, indent=1))
    if not s.get("trades"):
        return f"🧪 BACKTEST (simulation, not live) {period}: no trades. {BIASES}"
    weak = f"{s['weak_trades']} weak-market trades avg {s['weak_avg_r']:.2f}R" if s["weak_trades"] else "no weak-market trades"
    return (f"🧪 BACKTEST — historical simulation, NOT live — {period}, ₹{cfg['capital_inr']:,} notional\n"
            f"Trades {s['trades']} · avg {s['avg_r']:.2f}R net of costs · win rate {s['win_rate']:.0%} · "
            f"avg hold {s['avg_days']:.0f} days\n"
            f"Return {s['total_return']:.1%} ({s['cagr']:.1%}/yr) · worst drawdown {s['max_drawdown']:.1%}\n"
            f"{weak}\n"
            f"Go-live bar (D-048: ≥30 trades, ≥0.3R avg) {'met' if s['gate_d048'] else 'NOT met'} in simulation — "
            f"paper trading must still pass it.\n{BIASES}")


def main() -> int:
    try:
        msg = run()
    except Exception as e:
        alerts.send(f"❌ V4 backtest FAILED: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print(msg)
    alerts.send(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
