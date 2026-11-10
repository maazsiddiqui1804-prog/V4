"""Plain-English facts for the V4 app (D-108): what to do now, what's coming, how V4 is doing.
Pure functions over the repo's data files, so they can be tested. Read-only; never places orders (D-003).
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

AREA = {"chips": "Chips", "software_cloud": "Software & cloud", "hardware_networking": "Hardware & networking",
        "power": "Power for data centres"}


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "placeholders.yaml").read_text())


def q(sql: str, params=(), data: Path = DATA) -> pd.DataFrame:
    p = data / "v4.sqlite"
    if not p.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as c:
            return pd.read_sql(sql, c, params=params)
    except Exception:
        return pd.DataFrame()


def latest_plan(data: Path = DATA) -> dict | None:
    files = sorted((data / "briefs").glob("*.json")) if (data / "briefs").exists() else []
    return json.loads(files[-1].read_text()) if files else None


def next_first_of_month(today: dt.date) -> dt.date:
    return dt.date(today.year + (today.month == 12), today.month % 12 + 1, 1)


def next_quarter_start(today: dt.date) -> dt.date:
    for m in (1, 4, 7, 10):
        d = dt.date(today.year, m, 1)
        if d > today:
            return d
    return dt.date(today.year + 1, 1, 1)


def todos(today: dt.date, data: Path = DATA, c: dict | None = None) -> list[str]:
    """Things to act on now, in plain words. Empty list = nothing to do."""
    c = c or cfg()
    out = []
    month = today.strftime("%Y-%m")
    plan = latest_plan(data)
    if plan and plan["month"] == month:
        for b in plan["buys"]:
            out.append(f"Buy {b['shares']} {b['symbol']} — limit order at or below ₹{b['limit']:,.2f} (≈ ₹{b['amount']:,})")
        for h in plan["holdings"]:
            if h["action"] != "HOLD":
                extra = f" {h['shares']} shares" if h.get("shares") else ""
                out.append(f"{h['action'].title()}{extra} {h['symbol']} — {h['reason']}")
        if plan.get("leftover", 0) >= 1:
            out.append(f"Put the leftover ₹{plan['leftover']:,} in the liquid fund")
    flags = q("SELECT s.symbol, f.flag_type FROM red_flags f JOIN securities s USING(security_id) WHERE f.reviewed=0", data=data)
    for r in flags.itertuples():
        out.append(f"Read the red-flag filing for {r.symbol} ({r.flag_type.replace('_', ' ')}) and tell Claude: keep or sell")
    first = str(c["investment"]["portfolio"].get("first_brief_month", ""))
    imported = q("SELECT MAX(as_of) AS a FROM fundamentals WHERE source='screener'", data=data)
    last_import = (imported["a"].iloc[0] or "")[:7] if not imported.empty else ""
    if month >= first and last_import < month:
        out.append("Drop this month's Screener export into the GitHub inbox (data/inbox) — the buy list follows on Telegram")
    return out


def waiting(data: Path = DATA, c: dict | None = None) -> list[str]:
    """Decisions/one-off tasks for Maaz that aren't urgent."""
    c = c or cfg()
    us = c.get("us", {})
    out = []
    short = data / "us" / "shortlist.csv"
    if short.exists():
        s = pd.read_csv(short)
        n = int((s.get("zerodha_checked", pd.Series(dtype=str)).fillna("") == "").sum())
        if n:
            out.append(f"When Kite shows US stocks: log in and ask Claude to check the {n} US names")
    if not us.get("approved"):
        out.append("Approve the US numbers (before the first US buy)")
    if not (us.get("compliance") or {}).get("w8ben_signed"):
        out.append("Submit the W-8BEN form in Zerodha (before the first US buy)")
    if not c["trading"].get("paper_start"):
        out.append("After the GMAT: set up Kite Connect so paper trading can start")
    return out


def coming_up(today: dt.date, c: dict | None = None) -> list[tuple[str, str]]:
    c = c or cfg()
    first = str(c["investment"]["portfolio"].get("first_brief_month", ""))
    nxt = next_first_of_month(today)
    if nxt.strftime("%Y-%m") < first:
        nxt = dt.date.fromisoformat(first + "-01")
    out = [(f"{nxt:%-d %b}", "Drop the Screener export in the GitHub inbox → the monthly buy list arrives on Telegram")]
    out.append((f"{next_quarter_start(today):%-d %b}", "Quarterly report on Telegram"))
    if not c["trading"].get("paper_start"):
        out.append(("After the GMAT", "Paper trading starts (no real money until it proves itself)"))
    signed = (c.get("us", {}).get("compliance") or {}).get("w8ben_signed")
    if signed:
        out.append((f"31 Dec {dt.date.fromisoformat(signed).year + 3}", "W-8BEN expires — renew in Zerodha"))
    return out


def status(data: Path = DATA, c: dict | None = None) -> dict[str, str]:
    c = c or cfg()
    out = {}
    h = q("""SELECT COUNT(DISTINCT security_id) AS n, SUM(quantity*avg_price) AS cost FROM holdings_snapshots
             WHERE engine='investment' AND snapshot_date=(SELECT MAX(snapshot_date) FROM holdings_snapshots)""", data=data)
    if h.empty or not h["n"].iloc[0]:
        out["India investing"] = "Not started — first buys in December"
    else:
        out["India investing"] = f"{int(h['n'].iloc[0])} stocks, ₹{h['cost'].iloc[0]:,.0f} invested"
    short = data / "us" / "shortlist.csv"
    if short.exists():
        s = pd.read_csv(short)
        ok = int((s.get("zerodha_checked", pd.Series(dtype=str)).fillna("").str.lower() == "yes").sum())
        out["US investing"] = f"{len(s)} companies shortlisted · {ok} confirmed on Zerodha · no buys yet"
    else:
        out["US investing"] = "Shortlist not built yet"
    if c["trading"].get("paper_start"):
        out["Trading"] = f"Paper trading since {c['trading']['paper_start']}"
    else:
        out["Trading"] = "Paper trading not started (after the GMAT)"
    return out


def india_cards(data: Path = DATA, top: int = 10) -> tuple[str, list[dict]]:
    df = q("""SELECT l.list_month, l.rank, s.symbol, s.name, s.sector, l.score_total, l.buy_below, l.passes_guardrail,
              l.frozen_at FROM investment_lists l JOIN securities s USING(security_id)
              WHERE l.list_month=(SELECT MAX(list_month) FROM investment_lists) ORDER BY l.rank""", data=data)
    if df.empty:
        return "", []
    label = df["list_month"].iloc[0] + ("" if df["frozen_at"].notna().all() else " (preview — not final)")
    cards = []
    for r in df.head(top).itertuples():
        cards.append({"title": f"#{r.rank} {r.name} ({r.symbol})", "sub": r.sector or "",
                      "line": f"Overall score {r.score_total:.0f}/100",
                      "action": (f"✅ Buyable now — pay no more than ₹{r.buy_below:,.2f}" if r.passes_guardrail
                                 else "⏳ Too expensive right now — wait")})
    return label, cards


def us_cards(data: Path = DATA) -> list[dict]:
    p = data / "us" / "shortlist.csv"
    if not p.exists():
        return []
    s = pd.read_csv(p)
    rank = data / "us" / "ranking.csv"
    ranked = pd.read_csv(rank).set_index("ticker") if rank.exists() else pd.DataFrame()
    cards = []
    for r in s.itertuples():
        chk = str(getattr(r, "zerodha_checked", "") or "").lower()
        if chk == "yes" and r.ticker in ranked.index:
            g = ranked.loc[r.ticker]
            action = "✅ Ranked — see monthly list" if bool(g.get("passes_guardrail")) else "⏳ Too expensive vs growth — wait"
        elif chk == "yes":
            action = "✅ On Zerodha — prices next"
        elif chk == "no":
            action = "✖ Not available on Zerodha"
        else:
            action = "Waiting for the Kite check"
        cards.append({"title": f"#{int(r.qg_rank)} {str(r.name).title()} ({r.ticker})", "sub": AREA.get(r.layer, r.layer),
                      "line": f"Quality {r.score_quality:.0f}/100 · Growth {r.score_growth:.0f}/100", "action": action})
    return cards


def trading_summary(data: Path = DATA) -> dict:
    p = data / "backtest" / "summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def benchmark_lines(data: Path = DATA) -> pd.DataFrame:
    """D-122: chained median daily return of each benchmark's index funds (data/benchmarks/navs.csv)."""
    from statistics import median
    p = data / "benchmarks" / "navs.csv"
    if not p.exists():
        return pd.DataFrame()
    navs = pd.read_csv(p)
    names = {"nifty500": "Nifty 500", "quality30": "Quality 30", "momentum30": "Momentum 30", "nasdaq100": "Nasdaq-100"}
    out = {}
    for bench, g in navs.sort_values("date").groupby("benchmark"):
        last, level, line = {}, 100.0, {}
        for date, day in g.groupby("date"):
            rets = [r.nav / last[r.scheme_code] - 1 for r in day.itertuples() if last.get(r.scheme_code)]
            if rets:
                level *= 1 + median(rets)
            line[date] = level
            for r in day.itertuples():
                last[r.scheme_code] = r.nav
        out[names.get(bench, bench)] = line
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


# ---------------------------------------------------------------- app v2 data (2026-11-10)
APP = DATA / "app"


def latest_prices(data: Path = DATA) -> pd.DataFrame:
    p = data / "app" / "latest_prices.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else pd.DataFrame()


def series(data: Path = DATA) -> pd.DataFrame:
    p = data / "app" / "series.csv.gz"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else pd.DataFrame()


def nifty500(data: Path = DATA) -> pd.Series:
    p = data / "app" / "nifty500.csv"
    return pd.read_csv(p, parse_dates=["date"]).set_index("date")["close"] if p.exists() else pd.Series(dtype=float)


def india_plan(amount: float, data: Path = DATA, c: dict | None = None):
    """This month's India buy plan recomputed for any amount (same engine as the monthly brief).
    Returns (orders DataFrame, notes, list_month) or None when there is no list yet."""
    from v4.engines.investment import portfolio as pf
    c = c or cfg()
    lst = q("""SELECT l.list_month, l.rank, l.security_id, s.symbol, s.name, s.sector, l.buy_below, l.passes_guardrail,
              l.score_total FROM investment_lists l JOIN securities s USING(security_id)
              WHERE l.list_month=(SELECT MAX(list_month) FROM investment_lists) ORDER BY l.rank""", data=data)
    if lst.empty:
        return None
    px = latest_prices(data)
    price = dict(zip(px.get("symbol", []), px.get("close", [])))
    lst["current_price"] = lst["symbol"].map(price)
    lst["passes_guardrail"] = lst["passes_guardrail"].astype(bool) & (lst["current_price"] <= lst["buy_below"])
    hold = india_holdings(data)
    hold_in = hold.rename(columns={"price": "current_price"})[["security_id", "symbol", "quantity", "current_price", "sector"]] \
        if not hold.empty else pd.DataFrame(columns=["security_id", "symbol", "quantity", "current_price", "sector"])
    inv = c["investment"]
    rules = dict(inv["portfolio"], **inv["sells"], min_buy_inr=inv["min_buy_inr"])
    plan = pf.plan_buys(lst.dropna(subset=["current_price"]), hold_in, amount, rules)
    names = dict(zip(lst["symbol"], lst["name"]))
    orders = pd.DataFrame([{"Stock": o.symbol, "Company": names.get(o.symbol, ""), "Shares": o.shares,
                            "Pay at most (₹)": round(o.limit, 2), "Amount (₹)": round(o.amount), "Rank": o.rank,
                            "Type": "New" if o.kind == "new" else "Top-up"} for o in plan.orders])
    return orders, list(plan.notes) + ([f"Leftover ₹{plan.leftover:,.0f} → liquid fund"] if plan.leftover >= 1 else []), \
        lst["list_month"].iloc[0]


def india_list(data: Path = DATA) -> pd.DataFrame:
    lst = q("""SELECT l.rank AS Rank, s.symbol AS Stock, s.name AS Company, s.sector AS Sector,
              ROUND(l.score_total) AS Score, l.buy_below AS "Buy below (₹)", l.passes_guardrail
              FROM investment_lists l JOIN securities s USING(security_id)
              WHERE l.list_month=(SELECT MAX(list_month) FROM investment_lists) ORDER BY l.rank""", data=data)
    if lst.empty:
        return lst
    px = latest_prices(data)
    lst["Price now (₹)"] = lst["Stock"].map(dict(zip(px.get("symbol", []), px.get("close", []))))
    lst["Buyable now"] = lst["passes_guardrail"].astype(bool) & (lst["Price now (₹)"] <= lst["Buy below (₹)"])
    return lst.drop(columns=["passes_guardrail"])


def india_holdings(data: Path = DATA, engine: str = "investment") -> pd.DataFrame:
    h = q("""SELECT h.security_id, s.symbol, s.name, s.sector, h.quantity, h.avg_price FROM holdings_snapshots h
             JOIN securities s USING(security_id) WHERE s.market='IN' AND h.engine=? AND
             h.snapshot_date=(SELECT MAX(snapshot_date) FROM holdings_snapshots WHERE engine=?)""",
          (engine, engine), data=data)
    if h.empty:
        return h
    px = latest_prices(data)
    h["price"] = h["symbol"].map(dict(zip(px.get("symbol", []), px.get("close", []))))
    h["price"] = h["price"].fillna(h["avg_price"])
    h["invested"] = h["quantity"] * h["avg_price"]
    h["value"] = h["quantity"] * h["price"]
    h["gain_pct"] = h["value"] / h["invested"] - 1
    return h


def trading_today(data: Path = DATA) -> dict:
    p = data / "app" / "trading_today.json"
    return json.loads(p.read_text()) if p.exists() else {}


def us_shortlist(data: Path = DATA) -> pd.DataFrame:
    p = data / "us" / "shortlist.csv"
    if not p.exists():
        return pd.DataFrame()
    s = pd.read_csv(p)
    chk = s.get("zerodha_checked", pd.Series("", index=s.index)).fillna("").astype(str).str.lower()
    out = pd.DataFrame({"Rank": s["qg_rank"].astype(int), "Ticker": s["ticker"], "Company": s["name"].str.title(),
                        "Area": s["layer"].map(AREA).fillna(s["layer"]),
                        "Quality": s["score_quality"].round(), "Growth": s["score_growth"].round(),
                        "Reports in": s.get("currency", "USD"),
                        "On Zerodha": chk.map({"yes": "✅ Yes", "no": "✖ No"}).fillna("Not checked yet"),
                        "ROCE (worst of 3 yrs)": (s["roce_floor_3y"] * 100).round(0),
                        "Sales growth": (s["rev_growth"] * 100).round(0),
                        "Profit growth": (s["profit_growth"] * 100).round(0),
                        "Debt/equity": s["debt_equity"].round(2)})
    return out


def suggestions(data: Path = DATA) -> pd.DataFrame:
    """Every buy V4 suggested (from the saved monthly plans), whether you took it (it appears in your
    holdings afterwards) and what the price did since."""
    rows = []
    for f in sorted((data / "briefs").glob("*.json")) if (data / "briefs").exists() else []:
        p = json.loads(f.read_text())
        for b in p.get("buys", []):
            rows.append({"Month": p["month"], "Stock": b["symbol"], "Suggested at (₹)": b["limit"],
                         "Amount (₹)": b["amount"]})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    held = q("""SELECT s.symbol, MIN(h.snapshot_date) AS first_held FROM holdings_snapshots h
                JOIN securities s USING(security_id) WHERE h.engine='investment' GROUP BY s.symbol""", data=data)
    first = dict(zip(held.get("symbol", []), held.get("first_held", [])))
    df["Taken"] = [bool(first.get(s)) and first[s][:7] >= m for s, m in zip(df["Stock"], df["Month"])]
    px = latest_prices(data)
    df["Price now (₹)"] = df["Stock"].map(dict(zip(px.get("symbol", []), px.get("close", []))))
    df["Since suggestion"] = df["Price now (₹)"] / df["Suggested at (₹)"] - 1
    return df


def build(data: Path = DATA) -> dict:
    p = data / "app" / "build.json"
    return json.loads(p.read_text()) if p.exists() else {}


def jobs(data: Path = DATA) -> dict:
    p = data / "app" / "jobs.json"
    return json.loads(p.read_text()) if p.exists() else {}


# ---- "mark as done": saved to data/app/done.json in the repo when a GitHub key is set in Streamlit secrets
DONE = "data/app/done.json"


def load_done(data: Path = DATA) -> dict:
    p = data / "app" / "done.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_done(done: dict, token: str, repo: str = "maazsiddiqui1804-prog/V4") -> bool:
    """Write done.json back to GitHub (contents API). Returns True on success. Never logs the token."""
    import base64
    import requests
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{repo}/contents/{DONE}"
    cur = requests.get(url, headers=h, timeout=20)
    sha = cur.json().get("sha") if cur.status_code == 200 else None
    body = {"message": "App: mark to-dos done", "content": base64.b64encode(json.dumps(done, indent=1).encode()).decode(),
            "committer": {"name": "V4 app", "email": "v4-app@users.noreply.github.com"}}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=h, json=body, timeout=20)
    return r.status_code in (200, 201)
