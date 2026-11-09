"""Investment Engine, step 1: kill filters (D-023, D-116, D-123).

Plain English: before any stock is scored, it must not be fragile.
A stock is knocked out if ANY of these is true (numbers live in
config/placeholders.yaml and are placeholders until tested):

1. Loss: a loss in the last full year, the year before, or the trailing 12 months (D-116).
2. Debt: debt-to-equity above the cap.
3. Interest cover below the floor — skipped when debt is close to zero,
   because then there's little interest to cover.
4. Promoter pledge above the cap.
5. Cash conversion below the floor: over the last 2 years, operating cash flow
   divided by reported profit. Profit that never turns into cash is a warning sign.

A blank number counts as a fail (approved 2026-11-09): V4 never buys what it can't check.
Banks/NBFCs/insurers (D-114) and REITs (D-115) never get here at all.
Every result is saved with its reasons, so any exclusion can be explained.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from v4.db import ROOT, connect, init_db, DB_PATH

CONFIG = ROOT / "config" / "placeholders.yaml"
NEEDED = ["net_profit_last_year", "net_profit_preceding_year", "net_profit",
          "debt_to_equity", "interest_coverage_ratio", "pledged_percentage",
          "cash_from_operations_last_year", "cash_from_operations_preceding_year"]


def load_rules(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text())["investment"]["kill_filters"]


def investable_metrics(as_of: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    """One row per investable stock (not financial, not REIT, in this month's Nifty 500)."""
    with connect(db_path) as c:
        df = pd.read_sql(
            """SELECT s.security_id, s.symbol, f.metric, f.value
               FROM fundamentals f JOIN securities s USING(security_id)
               JOIN universe_membership u ON u.security_id = s.security_id
                    AND u.universe = 'NIFTY500' AND u.as_of = f.as_of
               WHERE f.as_of = ? AND s.is_financial = 0 AND s.is_reit = 0""",
            c, params=(as_of,))
    wide = df.pivot_table(index=["security_id", "symbol"], columns="metric", values="value")
    for col in NEEDED:
        if col not in wide:
            wide[col] = float("nan")
    return wide.reset_index()


def apply(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Adds 'passed' and 'reasons' columns. Pure function: easy to test."""
    def check(r) -> list[str]:
        why = []
        blank_fail = rules.get("blank_means_fail", True)

        profits = [r.net_profit_last_year, r.net_profit_preceding_year, r.net_profit]
        if any(pd.isna(p) for p in profits) and blank_fail:
            why.append("profit data missing")
        elif any(p < 0 for p in profits if pd.notna(p)):
            why.append("loss in last 2 years or trailing 12 months")

        de = r.debt_to_equity
        if pd.isna(de):
            if blank_fail:
                why.append("debt-to-equity missing")
        elif de > rules["max_debt_equity"]:
            why.append(f"debt-to-equity {de:.2f} > {rules['max_debt_equity']}")

        low_debt = pd.notna(de) and de < rules["near_zero_debt"]
        icr = r.interest_coverage_ratio
        if not low_debt:
            if pd.isna(icr):
                if blank_fail:
                    why.append("interest cover missing")
            elif icr < rules["min_interest_cover"]:
                why.append(f"interest cover {icr:.1f}× < {rules['min_interest_cover']}×")

        pl = r.pledged_percentage
        if pd.isna(pl):
            if blank_fail:
                why.append("pledge data missing")
        elif pl > rules["max_promoter_pledge_pct"]:
            why.append(f"promoter pledge {pl:.1f}% > {rules['max_promoter_pledge_pct']}%")

        cfo = [r.cash_from_operations_last_year, r.cash_from_operations_preceding_year]
        np2 = [r.net_profit_last_year, r.net_profit_preceding_year]
        if any(pd.isna(x) for x in cfo + np2):
            if blank_fail:
                why.append("cash-flow data missing")
        elif sum(np2) <= 0:
            why.append("no 2-year profit to convert")
        else:
            cc = sum(cfo) / sum(np2)
            if cc < rules["min_cash_conversion"]:
                why.append(f"cash conversion {cc:.2f} < {rules['min_cash_conversion']}")
        return why

    out = df.copy()
    out["reasons"] = out.apply(check, axis=1)
    out["passed"] = out["reasons"].map(lambda w: not w)
    return out


KINDS = ["missing", "loss", "no 2-year profit", "debt-to-equity", "interest cover",
         "promoter pledge", "cash conversion"]


def kind(reason: str) -> str:
    """Group a reason like 'debt-to-equity 2.25 > 1.5' under 'debt-to-equity'."""
    if "missing" in reason:
        return "data missing"
    return next((k for k in KINDS if reason.startswith(k)), reason)


def run(as_of: str, db_path: Path = DB_PATH, rules: dict | None = None) -> pd.DataFrame:
    init_db(db_path)
    res = apply(investable_metrics(as_of, db_path), rules or load_rules())
    with connect(db_path) as c:
        c.execute("DELETE FROM kill_filter_results WHERE as_of=?", (as_of,))
        c.executemany("INSERT INTO kill_filter_results VALUES (?,?,?,?)",
                      [(as_of, int(r.security_id), int(r.passed), "; ".join(r.reasons))
                       for r in res.itertuples()])
    return res


if __name__ == "__main__":
    import sys
    from collections import Counter
    as_of = sys.argv[1]
    res = run(as_of)
    print(f"{as_of}: {res.passed.sum()} of {len(res)} investable stocks pass the kill filters")
    kinds = Counter(kind(r) for rs in res.reasons for r in set(rs))
    print("Knock-outs by reason (a stock can fail several):")
    for k, v in kinds.most_common():
        print(f"  {v:>4}  {k}")
