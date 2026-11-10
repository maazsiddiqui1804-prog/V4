"""Telegram digest — so Maaz never has to open the app to know what to do (D-004, D-138).

  python -m v4.jobs.digest weekly    Mondays 08:53 IST: everything waiting on you, what's coming, how V4 is doing
  python -m v4.jobs.digest monthly   1st of the month 09:23 IST: the Screener drop reminder (only if it's due)
Every message ends with the app link (v4/alerts.py). Items you ticked as done in the app are left out.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

from v4 import app_logic as L


def kite_line(c_app: dict) -> str | None:
    if not c_app.get("kite_enabled"):
        return None
    last = L.last_kite_login()
    url = c_app["url"].rstrip("/") + "/kite"
    return f"🔑 Kite login (daily, after 6 AM): {url}" + (f" · last login {last}" if last else "")


def weekly(today: dt.date) -> str:
    c, app = L.cfg(), L.app_cfg()
    done = {k for k, v in L.load_done().items() if v}
    todo = [x for x in L.todos(today, c=c) if x not in done]
    wait = [x for x in L.waiting(c=c) if x not in done]
    b = L.build()
    mine = [f"{t['task_id']}: {t['task']}" for t in b.get("tasks", [])
            if t.get("owner") == "Maaz" and t.get("status") != "Done"]
    mine = [x for x in mine if x not in done]
    lines = [f"🗓️ V4 weekly — {today:%a %d %b}"]
    lines.append("\nDO NOW:")
    lines += [f"• {x}" for x in todo] or ["• Nothing this week ✅"]
    k = kite_line(app)
    if k:
        lines.append(k)
    waiting = mine or wait            # the dashboard task list is the full version; fall back to the short list
    if waiting:
        lines.append("\nWAITING ON YOU (no rush):")
        lines += [f"• {x}" for x in waiting]
    lines.append("\nCOMING UP:")
    lines += [f"• {w} — {what}" for w, what in L.coming_up(today, c=c)]
    t = L.trading_today()
    if t:
        lines.append(f"\nTRADING ({'paper' if c['trading'].get('paper_start') else 'watch-only'}): "
                     f"{len(t.get('new', []))} new signals, {len(t.get('watchlist', []))} near breakout"
                     + (f" · {t['gate']}" if t.get("gate") else ""))
    flags = L.q("SELECT COUNT(*) AS n FROM red_flags WHERE reviewed=0")
    if not flags.empty and int(flags["n"].iloc[0]):
        lines.append(f"🚩 {int(flags['n'].iloc[0])} red flag(s) waiting for your review")
    return "\n".join(lines)


def monthly(today: dt.date) -> str | None:
    c = L.cfg()
    first = str(c["investment"]["portfolio"].get("first_brief_month", ""))
    month = today.strftime("%Y-%m")
    if month < first:
        return None
    imp = L.q("SELECT MAX(as_of) AS a FROM fundamentals WHERE source='screener'")
    last = (imp["a"].iloc[0] or "")[:7] if not imp.empty else ""
    if last >= month:
        return None
    return ("📥 V4 monthly: time for the Screener export.\n"
            "1. screener.in → your V4 screen → Export\n"
            "2. github.com/maazsiddiqui1804-prog/V4 → data/inbox → Add file → Upload\n"
            "The buy list follows on Telegram within ~10 minutes.")


def main(mode: str) -> int:
    from v4 import alerts
    today = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
    try:
        msg = weekly(today) if mode == "weekly" else monthly(today)
    except Exception as e:
        alerts.send(f"❌ V4 {mode} digest FAILED: {e}")
        return 1
    if msg:
        print(msg)
        alerts.send(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
