"""Daily app refresh (weekdays after the close). Read-only: never places orders (D-003).

1. India prices: adds the latest days to the full history (kept on the separate `prices` branch so
   the main branch doesn't grow by megabytes every day).
2. Small snapshot files for the app on main (data/app/): latest price + trend facts for every Nifty 500
   stock, and one year of daily closes for the stocks the app charts (holdings, this month's list,
   past suggestions, today's trading signals and watchlist).
3. Forward-tracking of every frozen India list vs the Nifty 500 (D-063) → data/app/list_tracking.csv.
4. India Trading "B2" evening plan (D-137) — WATCH-ONLY until paper trading starts (D-130).
5. Health of every scheduled job, for the app's Build page.

python -m v4.jobs.daily_app <full-history-dir>
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
import yaml

from v4.db import ROOT, connect, DB_PATH
from v4.engines.investment import tracking
from v4.engines.trading import daily, signals as sg
from v4.importers import india_prices as ip

APP = ROOT / "data" / "app"


def watch_symbols(db_path=DB_PATH, extra=()) -> set[str]:
    out = set(extra)
    with connect(db_path) as c:
        out |= {r[0] for r in c.execute("""SELECT DISTINCT s.symbol FROM holdings_snapshots h
                                           JOIN securities s USING(security_id) WHERE s.market='IN'""")}
        out |= {r[0] for r in c.execute("""SELECT s.symbol FROM investment_lists l JOIN securities s USING(security_id)
                                           WHERE l.rank<=30 AND l.list_month=(SELECT MAX(list_month) FROM investment_lists)""")}
    for f in (ROOT / "data" / "briefs").glob("*.json"):
        out |= {b["symbol"] for b in json.loads(f.read_text()).get("buys", [])}
    return out


def snapshot(px: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """One row per stock: latest close, 1-day and 1-year change, 52-week high, 50/200-day averages."""
    px = px.sort_values(["symbol", "date"])
    g = px.groupby("symbol")["close"]
    snap = px.groupby("symbol").tail(1)[["symbol", "date", "close"]].set_index("symbol")
    snap["chg_1d"] = g.apply(lambda s: s.iloc[-1] / s.iloc[-2] - 1 if len(s) > 1 else None)
    snap["chg_1y"] = g.apply(lambda s: s.iloc[-1] / s.iloc[-253] - 1 if len(s) > 252 else None)
    snap["high_52w"] = g.apply(lambda s: s.iloc[-252:].max())
    snap["dma50"] = g.apply(lambda s: s.iloc[-50:].mean() if len(s) >= 50 else None)
    snap["dma200"] = g.apply(lambda s: s.iloc[-200:].mean() if len(s) >= 200 else None)
    return snap.reset_index()


def job_health(repo: str | None, token: str | None) -> list[dict]:
    if not repo or not token:
        return []
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    wfs = requests.get(f"https://api.github.com/repos/{repo}/actions/workflows", headers=h, timeout=30).json()
    out = []
    for w in wfs.get("workflows", []):
        runs = requests.get(f"https://api.github.com/repos/{repo}/actions/workflows/{w['id']}/runs",
                            headers=h, params={"per_page": 1}, timeout=30).json().get("workflow_runs", [])
        r = runs[0] if runs else {}
        out.append({"job": w["name"], "last_run": (r.get("created_at") or "")[:16].replace("T", " "),
                    "result": r.get("conclusion") or r.get("status") or "never run"})
    return out


def kite_today():
    """Kite client if Kite is switched on and Maaz logged in today; else (None, reason)."""
    app = yaml.safe_load((ROOT / "config" / "app.yaml").read_text())
    if not app.get("kite_enabled"):
        return None, "off"
    from v4.broker import kite
    k = kite.from_env()
    return (k, "ok") if k else (None, "no login today")


def missed_streak(checks: list[str], today: dt.date) -> int:
    """Consecutive weekdays (before today) with no Kite login — the D-049 tripwire counter."""
    done = set(checks)
    n, d = 0, today - dt.timedelta(days=1)
    while n < 10:
        if d.weekday() < 5:
            if d.isoformat() in done:
                break
            n += 1
        d -= dt.timedelta(days=1)
    return n


def run(history_dir: Path) -> str:
    from v4 import alerts
    from v4.engines.trading import paper
    cfg = yaml.safe_load((ROOT / "config" / "placeholders.yaml").read_text())["trading"]
    k, kstate = kite_today()
    today = dt.date.today()
    checks_p = APP / "checks.json"
    checks = json.loads(checks_p.read_text()) if checks_p.exists() else []
    if k:
        checks = sorted(set(checks) | {today.isoformat()})[-60:]
    hist, hidx = history_dir / "india_daily.csv.gz", history_dir / "nifty500_index.csv"
    if hist.exists():
        old = pd.read_csv(hist, parse_dates=["date"])
        if k:                                   # Kite is the price source once it's on (D-080/D-106)
            from v4.broker import kite_prices
            new, close, missing = kite_prices.recent(k, sorted(old["symbol"].unique()))
        else:
            new, close, missing = ip.fetch_frame("1mo")
        px = ip.merge(old, new)
        oi = pd.read_csv(hidx, parse_dates=["date"]).set_index("date")["close"]
        idx = pd.concat([oi, close]).groupby(level=0).last().sort_index()
    else:
        px, idx, missing = ip.fetch_frame("4y")
    history_dir.mkdir(parents=True, exist_ok=True)
    px.to_csv(hist, index=False, float_format="%.4f", compression="gzip")
    idx.rename("close").to_csv(hidx, float_format="%.2f", index_label="date")

    clean, fixes = ip.fix_unadjusted(px)
    sectors = dict(ip.universe().itertuples(index=False, name=None))
    recent = clean[clean["date"] >= clean["date"].max() - pd.Timedelta(days=600)]
    paper_start = cfg.get("paper_start")
    if paper_start:
        warm = pd.Timestamp(paper_start) - pd.Timedelta(days=500)     # enough history for the 52-week/200-day rules
        pr = paper.replay(clean[clean["date"] >= warm], idx, sectors, cfg, start=str(paper_start))
        positions, equity = pr["positions"], pr["equity"]
        pr["trades"].to_csv(APP / "paper_trades.csv", index=False)
    else:
        positions, equity = [], float(cfg["capital_inr"])
    plan = daily.evening_plan(recent, idx, sectors, positions, equity, cfg)
    streak = missed_streak(checks, today)
    if paper_start and streak >= 3:          # D-049: 3+ missed daily checks → no new trades until resumed
        plan["skipped"] = [(n["symbol"], "tripwire: 3+ missed daily logins") for n in plan["new"]] + plan["skipped"]
        plan["new"] = []
    plan["stops"] = {p.symbol: round(p.stop, 2) for p in positions}
    plan["mode"] = ("PAPER" if paper_start else "WATCH-ONLY (paper trading starts after the GMAT)")
    if paper_start:
        plan["gate"] = paper.gate_line(pr["gate"])
        if k:
            alerts.send(daily.render(plan, "PAPER — simulated, not real money") + "\n" + plan["gate"])
        elif kstate == "no login today":
            alerts.send("⚠️ No Kite login today, so tonight's paper-trading prices came from the backup source. "
                        f"Missed days in a row: {streak + 1}. At 3, new trades pause (D-049). Log in: open the app → Kite.")

    APP.mkdir(parents=True, exist_ok=True)
    snap = snapshot(clean[clean["date"] >= clean["date"].max() - pd.Timedelta(days=400)], cfg)
    snap["sector"] = snap["symbol"].map(sectors)
    snap.to_csv(APP / "latest_prices.csv", index=False, float_format="%.4f")
    syms = watch_symbols(extra=[n["symbol"] for n in plan["new"]] + [w["symbol"] for w in plan["watchlist"]])
    series = clean[(clean["symbol"].isin(syms)) & (clean["date"] >= clean["date"].max() - pd.Timedelta(days=370))]
    series[["date", "symbol", "close"]].to_csv(APP / "series.csv.gz", index=False, float_format="%.2f", compression="gzip")
    ix = idx[idx.index >= idx.index.max() - pd.Timedelta(days=370)]
    ix.rename("close").to_csv(APP / "nifty500.csv", float_format="%.2f", index_label="date")
    with connect(DB_PATH) as c:
        frozen = pd.read_sql("""SELECT l.list_month, s.symbol, l.rank, l.score_quality, l.score_growth, l.score_momentum,
                                l.score_total, l.passes_guardrail, l.frozen_at FROM investment_lists l
                                JOIN securities s USING(security_id) WHERE l.frozen_at IS NOT NULL""", c)
    tracking.track(frozen, clean[["date", "symbol", "close"]], idx).to_csv(APP / "list_tracking.csv", index=False,
                                                                           float_format="%.5f")
    (APP / "trading_today.json").write_text(json.dumps(plan, indent=1, default=str))
    checks_p.write_text(json.dumps(checks))
    (APP / "jobs.json").write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                                               "jobs": job_health(os.environ.get("GITHUB_REPOSITORY"),
                                                                  os.environ.get("GITHUB_TOKEN"))}, indent=1))
    return (f"App refreshed: prices to {px['date'].max():%d %b}, {len(syms)} charted stocks, "
            f"{len(plan['new'])} trading signals, {len(plan['watchlist'])} on the watchlist (watch-only)."
            + (f" Missing today: {len(missing)} stocks." if missing else ""))


def main() -> int:
    from v4 import alerts
    try:
        msg = run(Path(sys.argv[1]))
    except Exception as e:
        alerts.send(f"❌ V4 daily app refresh FAILED: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print(msg)                      # no Telegram on success: daily noise; failures always alert
    return 0


if __name__ == "__main__":
    sys.exit(main())
