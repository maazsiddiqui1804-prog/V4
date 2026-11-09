"""Investment Engine, step 2: score the stocks that passed the kill filters (D-099, D-103, D-124).

Plain English:
- Every number is turned into a rank from 0 to 100 among the survivors, so one
  extreme figure can't swamp the rest (D-124). Missing numbers rank at the bottom.
- Quality (D-024): the LOWEST of the 3-, 5- and 10-year average ROCE (high only if
  high in every period), blended equally with 2-year cash conversion.
- Growth (D-024 "steady"): for sales and for profit, the lower of 3- and 5-year growth.
- Momentum (D-099, lookback D-124): average rank of 6- and 12-month price returns.
- Weights: normal market 40/30/30; weak market (Nifty 500 below its 200-day
  average, D-103) 55/30/15. If the market signal can't be worked out, the cautious
  weak-market weights are used and the report says so.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from v4.db import ROOT, connect, init_db, DB_PATH
from v4.engines.investment import filters as kf
from v4.importers.benchmarks import composite

CONFIG = ROOT / "config" / "placeholders.yaml"
SCORE_METRICS = [
    "average_return_on_capital_employed_3years", "average_return_on_capital_employed_5years",
    "average_return_on_capital_employed_10years",
    "sales_growth_3years", "sales_growth_5years", "profit_growth_3years", "profit_growth_5years",
    "return_over_6months", "return_over_1year",
]


def pct(s: pd.Series) -> pd.Series:
    """Rank 0–100 among the group; missing values get 0."""
    return (s.rank(pct=True) * 100).fillna(0.0)


def regime(db_path: Path = DB_PATH, window: int = 200) -> tuple[str, str]:
    """D-103: 'weak' if the Nifty 500 benchmark line is below its 200-day average."""
    line = composite("nifty500", db_path)
    if len(line) < window:
        return "weak", f"market signal unavailable ({len(line)} of {window} days of history) — using cautious weights"
    levels = [v for _, v in line]
    avg = sum(levels[-window:]) / window
    last = levels[-1]
    state = "normal" if last >= avg else "weak"
    return state, f"Nifty 500 line {last:.1f} vs 200-day average {avg:.1f} → {state} market"


def score(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """df: one row per surviving stock with SCORE_METRICS + cash conversion inputs."""
    out = df.copy()
    roce = out[["average_return_on_capital_employed_3years",
                "average_return_on_capital_employed_5years",
                "average_return_on_capital_employed_10years"]]
    # lowest available, but need at least two periods to call anything "consistent"
    out["roce_floor"] = roce.min(axis=1).where(roce.notna().sum(axis=1) >= 2)
    cfo = out["cash_from_operations_last_year"] + out["cash_from_operations_preceding_year"]
    np2 = out["net_profit_last_year"] + out["net_profit_preceding_year"]
    out["cash_conversion"] = (cfo / np2).where(np2 > 0)
    out["score_quality"] = (pct(out["roce_floor"]) + pct(out["cash_conversion"])) / 2

    sales = out[["sales_growth_3years", "sales_growth_5years"]].min(axis=1)
    profit = out[["profit_growth_3years", "profit_growth_5years"]].min(axis=1)
    out["score_growth"] = (pct(sales) + pct(profit)) / 2

    out["score_momentum"] = (pct(out["return_over_6months"]) + pct(out["return_over_1year"])) / 2

    w = weights
    total = w["quality"] + w["growth"] + w["momentum"]
    out["score_total"] = (out["score_quality"] * w["quality"] + out["score_growth"] * w["growth"]
                          + out["score_momentum"] * w["momentum"]) / total
    out = out.sort_values("score_total", ascending=False).reset_index(drop=True)
    out["rank"] = range(1, len(out) + 1)
    return out


def run(as_of: str, db_path: Path = DB_PATH) -> tuple[pd.DataFrame, str]:
    init_db(db_path)
    cfg = yaml.safe_load(CONFIG.read_text())["investment"]
    filt = kf.run(as_of, db_path)
    survivors = filt[filt["passed"]].copy()
    for col in SCORE_METRICS:
        if col not in survivors:
            survivors[col] = float("nan")
    state, note = regime(db_path)
    weights = cfg["score_weights"]["normal" if state == "normal" else "weak_market"]
    ranked = score(survivors, weights)
    month = as_of[:7]
    with connect(db_path) as c:
        frozen = c.execute("SELECT COUNT(*) FROM investment_lists WHERE list_month=? AND frozen_at IS NOT NULL",
                           (month,)).fetchone()[0]
        if frozen:
            raise RuntimeError(f"List for {month} is already frozen; it can't be re-scored (D-063)")
        c.execute("DELETE FROM investment_lists WHERE list_month=?", (month,))
        c.executemany(
            """INSERT INTO investment_lists (list_month, security_id, rank, score_quality, score_growth,
                   score_momentum, score_total, regime) VALUES (?,?,?,?,?,?,?,?)""",
            [(month, int(r.security_id), int(r.rank), r.score_quality, r.score_growth,
              r.score_momentum, r.score_total, state) for r in ranked.itertuples()])
    return ranked, f"Weights {weights['quality']}/{weights['growth']}/{weights['momentum']} — {note}"
