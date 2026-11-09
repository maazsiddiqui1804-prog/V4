"""Quarterly report (D-066 review calendar: Jan/Apr/Jul/Oct). Facts for the review; changes nothing.

Sections: investment sleeve vs benchmarks (D-064/D-065, once there are holdings), trading paper
progress vs the go-live bar (D-048) and the backtest (simulation), red flags still open, US
safeguards (D-132), cloud health. Saved to data/reports/<quarter>.md and sent to Telegram.
Rule changes are NOT made by this job: quarterly = fixes only, January = strategy (D-066).
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd
import yaml

from v4 import alerts
from v4.db import ROOT, connect, DB_PATH
from v4.engines.us import brief as us_brief

REPORTS = ROOT / "data" / "reports"


def quarter(d: dt.date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def build(today: dt.date | None = None, db_path=DB_PATH) -> str:
    today = today or dt.date.today()
    cfg = yaml.safe_load((ROOT / "config" / "placeholders.yaml").read_text())
    L = [f"📑 V4 quarterly report — {quarter(today)} (as of {today:%d %b %Y})",
         "Quarterly reviews are for fixes only (bugs, data, costs, breaches); strategy changes wait for January (D-066)."]

    L.append("\n1. INVESTMENT SLEEVE (D-064/D-065)")
    with connect(db_path) as c:
        n_hold = c.execute("SELECT COUNT(*) FROM holdings_snapshots WHERE engine='investment'").fetchone()[0]
        months = [r[0] for r in c.execute("SELECT DISTINCT list_month FROM investment_lists WHERE frozen_at IS NOT NULL")]
        flags = c.execute("SELECT COUNT(*) FROM red_flags WHERE reviewed=0").fetchone()[0]
    if not n_hold:
        L.append("No holdings yet — comparison vs Nifty 500 and Quality 30 index funds starts after the first buys.")
    else:
        L.append(f"{n_hold} holding records; frozen monthly lists: {len(months)}. "
                 "12-month warning from the first list's anniversary; 3-year kill test after 36 months.")
    L.append(f"Open red flags awaiting your review: {flags}")

    L.append("\n2. TRADING ENGINE")
    summ_p = ROOT / "data" / "backtest" / "summary.json"
    if summ_p.exists():
        s = json.loads(summ_p.read_text())
        L.append(f"Backtest (SIMULATION, not live) {s.get('period')}: {s.get('trades')} trades, avg {s.get('avg_r', 0):.2f}R, "
                 f"worst drawdown {s.get('max_drawdown', 0):.0%}; go-live bar met in simulation: {s.get('gate_d048')}.")
    L.append("Paper trading: starts after the GMAT (D-130); progress vs D-048 shows here once running.")

    L.append("\n3. US")
    L += [x for x in us_brief.section(cfg.get("us", {}), today)[1:]]

    L.append("\n4. PLACEHOLDERS STILL UNTESTED")
    L.append("All engine cut-offs in config/placeholders.yaml remain starting values until evidence (≥30 trades, D-066).")
    return "\n".join(L)


def main() -> int:
    try:
        msg = build()
    except Exception as e:
        alerts.send(f"❌ V4 quarterly report FAILED: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{quarter(dt.date.today())}.md").write_text(msg)
    print(msg)
    for i in range(0, len(msg), 3900):
        alerts.send(msg[i:i + 3900])
    return 0


if __name__ == "__main__":
    sys.exit(main())
