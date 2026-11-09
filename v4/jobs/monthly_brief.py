"""Monthly India brief (D-026, D-063, D-108, D-126). Runs after the monthly import.

Plain English:
1. Find this month's data. If the month's ranked list isn't frozen yet: run kill
   filters → score → guardrail, then FREEZE the list (D-063: never re-scored).
   If already frozen (e.g. re-run with a different amount): reuse it as is.
2. Verdict on every holding (sell / trim / watch / review / hold).
3. Buy plan for this month's amount (default from config, or MONTHLY_AMOUNT override).
4. Send one Telegram brief: orders first, then verdicts, then the top 20.
V4 never places orders (D-003): Maaz decides and places them.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

from v4 import alerts
from v4.db import ROOT, connect, init_db, DB_PATH
from v4.engines.investment import filters as kf, score as sc, guardrail, portfolio as pf, sells as sl, redflags as rf
from v4.engines.us import brief as us_brief

CONFIG = ROOT / "config" / "placeholders.yaml"


class SkipBrief(Exception):
    """Not an error: a month before the first real brief."""


def latest_as_of(db_path: Path) -> str:
    with connect(db_path) as c:
        as_of = c.execute("SELECT MAX(as_of) FROM fundamentals WHERE source='screener'").fetchone()[0]
    if not as_of:
        raise RuntimeError("No Screener data in the database yet")
    return as_of


def month_frozen(month: str, db_path: Path) -> bool:
    with connect(db_path) as c:
        return bool(c.execute("SELECT COUNT(*) FROM investment_lists WHERE list_month=? AND frozen_at IS NOT NULL",
                              (month,)).fetchone()[0])


def freeze(month: str, db_path: Path) -> None:
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with connect(db_path) as c:
        c.execute("UPDATE investment_lists SET frozen_at=? WHERE list_month=? AND frozen_at IS NULL", (stamp, month))


def load_month(as_of: str, db_path: Path, cfg: dict) -> tuple[pd.DataFrame, str]:
    """This month's ranked list (frozen), joined with today's metrics for prices and guardrail reasons."""
    month = as_of[:7]
    with connect(db_path) as c:
        lst = pd.read_sql("SELECT * FROM investment_lists WHERE list_month=?", c, params=(month,))
        regime = lst["regime"].iloc[0] if len(lst) else "unknown"
    metrics = kf.investable_metrics(as_of, db_path)
    df = lst.merge(metrics, on="security_id", how="left")
    df["passes_guardrail"] = df["passes_guardrail"].astype(bool)
    df = guardrail.apply(df, cfg["valuation"]).assign(passes_guardrail=df["passes_guardrail"])
    return df.sort_values("rank").reset_index(drop=True), regime


def previous_ranks(month: str, db_path: Path) -> dict:
    with connect(db_path) as c:
        prev = c.execute("SELECT MAX(list_month) FROM investment_lists WHERE list_month<? AND frozen_at IS NOT NULL",
                         (month,)).fetchone()[0]
        if not prev:
            return {}
        return dict(c.execute("SELECT security_id, rank FROM investment_lists WHERE list_month=?", (prev,)).fetchall())


def open_red_flags(db_path: Path) -> set:
    with connect(db_path) as c:
        return {r[0] for r in c.execute("SELECT DISTINCT security_id FROM red_flags WHERE reviewed=0")}


def build(db_path: Path = DB_PATH, amount: float | None = None) -> str:
    init_db(db_path)
    cfg = yaml.safe_load(CONFIG.read_text())["investment"]
    as_of = latest_as_of(db_path)
    month = as_of[:7]
    first = str(cfg["portfolio"].get("first_brief_month", ""))
    if first and month < first:
        raise SkipBrief(f"No brief for {month}: the first real brief is {first} (Maaz's decision, 2026-11-09). "
                        "Data was imported; nothing was scored or frozen.")
    rf.load_into_db(db_path=db_path)
    note = ""
    if not month_frozen(month, db_path):
        _, note = sc.run(as_of, db_path)
        freeze(month, db_path)
        list_note = f"List for {month} scored and frozen."
    else:
        list_note = f"List for {month} was already frozen — reused, not re-scored."
    ranked, regime = load_month(as_of, db_path, cfg)
    ranked = pf.with_sector(ranked, db_path)

    with connect(db_path) as c:
        filt = pd.read_sql("SELECT security_id, passed, reasons FROM kill_filter_results WHERE as_of=?", c,
                           params=(as_of,))
    filt["reasons"] = filt["reasons"].fillna("").map(lambda s: [x for x in s.split("; ") if x])
    holdings = pf.holdings_frame(as_of, db_path)
    rules = dict(cfg["portfolio"], **cfg["sells"], min_buy_inr=cfg["min_buy_inr"])
    flags = open_red_flags(db_path)
    v = sl.verdicts(holdings, filt, ranked, previous_ranks(month, db_path), flags, rules)
    blocked = flags | {x.security_id for x in v if x.action == "SELL"}

    amount = float(amount if amount is not None else cfg["portfolio"]["monthly_amount_inr"])
    plan = pf.plan_buys(ranked, holdings, amount, rules, blocked_ids=blocked)
    msg = render(month, amount, regime, note, list_note, plan, v, ranked)
    us_cfg = yaml.safe_load(CONFIG.read_text()).get("us", {})
    return msg + "\n" + "\n".join(us_brief.section(us_cfg))


def render(month, amount, regime, note, list_note, plan, verdicts, ranked) -> str:
    L = [f"📊 V4 monthly — {month} · adding ₹{amount:,.0f}",
         f"Market: {regime}" + (f" ({note})" if note else "")]
    L.append("\nBUY (place limit orders; don't pay above the limit):")
    if plan.orders:
        for i, o in enumerate(plan.orders, 1):
            L.append(f"{i}. {o.symbol} — {o.shares} shares ≈ ₹{o.amount:,.0f}, limit ≤ ₹{o.limit:,.2f} (rank {o.rank})")
    else:
        L.append("— none this month")
    if plan.leftover >= 1:
        L.append(f"Leftover ₹{plan.leftover:,.0f} → liquid fund")
    acts = [x for x in verdicts if x.action != "HOLD"]
    holds = [x for x in verdicts if x.action == "HOLD"]
    L.append("\nHOLDINGS:")
    if not verdicts:
        L.append("— none yet")
    for x in acts:
        extra = f" {x.shares} shares" if x.shares else ""
        L.append(f"{x.action}{extra} {x.symbol} — {x.reason}")
    if holds:
        L.append(f"HOLD {len(holds)}: " + ", ".join(x.symbol for x in holds))
    if plan.notes:
        L.append("\nNOTES:")
        L += [f"• {n}" for n in plan.notes[:8]]
    L.append("\nTOP 20 (✅ buyable now · ❌ above buy-below or PEG too high):")
    for r in ranked.head(20).itertuples():
        bb = f"₹{r.buy_below:,.0f}" if pd.notna(r.buy_below) else "—"
        L.append(f"{int(r.rank):>2}. {r.symbol} {r.score_total:.0f} · buy-below {bb} {'✅' if r.passes_guardrail else '❌'}")
    L.append(f"\n{list_note} Starting numbers are untested placeholders. You decide; V4 never places orders. "
             "If you deviate, log the reason (D-016).")
    return "\n".join(L)


BRIEFS = ROOT / "data" / "briefs"


def save_brief(msg: str) -> None:
    """Keep each month's brief as a file so the dashboard can show it (D-108 Action view)."""
    month = msg.split("—", 1)[1].split("·")[0].strip() if "—" in msg else "latest"
    BRIEFS.mkdir(parents=True, exist_ok=True)
    (BRIEFS / f"{month}.md").write_text(msg)


def main() -> int:
    raw = os.environ.get("MONTHLY_AMOUNT", "").replace(",", "").strip()
    try:
        amount = float(raw) if raw else None
        msg = build(amount=amount)
    except SkipBrief as s:
        print(s)
        alerts.send(f"ℹ️ {s}")
        return 0
    except Exception as e:
        alerts.send(f"❌ V4 monthly brief FAILED: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print(msg)
    save_brief(msg)
    for i in range(0, len(msg), 3900):   # Telegram's limit is 4096 characters per message
        alerts.send(msg[i:i + 3900])
    return 0


if __name__ == "__main__":
    sys.exit(main())
