"""Kite-day operations (D-081, D-109). Idle until config/app.yaml → kite_enabled is true.

  python -m v4.jobs.kite_ops remind     08:47 and 16:03 IST: if not logged in today, Telegram a one-tap login link
  python -m v4.jobs.kite_ops midday     every ~30 min in market hours: paper stop hit / watchlist trigger crossed
Read-only; never places orders (D-003). Each alert is sent at most once per stock per day.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import yaml

from v4.db import ROOT

APP = ROOT / "data" / "app"


def app_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "app.yaml").read_text())


def midday_alerts(quotes: dict, plan: dict, already: set[str]) -> list[tuple[str, str]]:
    """quotes: {'NSE:SYM': {'last_price': x}}. Returns new (key, message) pairs."""
    out = []
    for s, action, why in plan.get("actions", []):
        q = quotes.get(f"NSE:{s}", {}).get("last_price")
        stop = plan.get("stops", {}).get(s)
        if q is not None and stop and q <= stop and f"stop:{s}" not in already:
            out.append((f"stop:{s}", f"🛑 {s} at ₹{q:,.2f} — at/below its stop ₹{stop:,.2f}. Your GTT should have sold it; check Kite."))
    for w in plan.get("watchlist", []):
        q = quotes.get(f"NSE:{w['symbol']}", {}).get("last_price")
        if q is not None and q >= w["trigger"] and f"trig:{w['symbol']}" not in already:
            out.append((f"trig:{w['symbol']}", f"👀 {w['symbol']} ₹{q:,.2f} crossed its trigger ₹{w['trigger']:,.2f} intraday. "
                                                 "It's a signal only if it CLOSES above on heavy volume — tonight's plan decides."))
    return out


def main(mode: str) -> int:
    from v4 import alerts
    from v4.broker import kite
    if not app_cfg().get("kite_enabled"):
        print("Kite is switched off (config/app.yaml) — nothing to do.")
        return 0
    k = kite.from_env()
    url = app_cfg()["url"].rstrip("/") + "/kite"
    try:
        if mode == "remind":
            if k is None:
                alerts.send(f"🔑 Kite isn't logged in today. One tap: {url} → Log in to Kite (tonight's run needs it).")
            return 0
        if mode == "midday":
            if k is None:
                return 0
            plan = json.loads((APP / "trading_today.json").read_text()) if (APP / "trading_today.json").exists() else {}
            syms = {s for s, _, _ in plan.get("actions", [])} | {w["symbol"] for w in plan.get("watchlist", [])}
            if not syms:
                return 0
            state_p = APP / "midday_state.json"
            state = json.loads(state_p.read_text()) if state_p.exists() else {}
            today = dt.date.today().isoformat()
            already = set(state.get(today, []))
            new = midday_alerts(k.ohlc([f"NSE:{s}" for s in sorted(syms)]), plan, already)
            for _, m in new:
                alerts.send(m)
            state = {today: sorted(already | {key for key, _ in new})}
            state_p.write_text(json.dumps(state))
            return 0
    except Exception as e:
        alerts.send(f"❌ V4 Kite {mode} check FAILED: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
