"""US Investment Engine: kill filters + shortlist score (D-023, D-024, D-135, D-136).

Plain English. Inputs are each company's yearly SEC figures (fundamentals.py).
1. Kill filters (D-023), checked on the last 3 full years (SEC gives real annual
   history, so "losses in last 3 years" is exact here, unlike India's D-116):
   loss in any of the last 3 years · debt-to-equity too high · interest cover too
   low (skipped when debt ≈ 0) · 3-year cash conversion too low. Blank = fail.
   (Promoter pledge is India-only.)
2. Shortlist score (D-136) — quality + growth only, no prices needed:
   Quality (D-024, 3-year window for the AI universe): lowest yearly ROCE of the
   last 3 years, + 3-year cash conversion, ranked 0–100.
   Growth: for revenue and for net profit, the lower of last-year growth and
   3-year average growth (rewards steady growth), ranked 0–100.
   Shortlist rank = quality and growth at their 40:30 weights (D-099).
All cut-offs come from config/placeholders.yaml → us: section (PLACEHOLDERS pending approval).
"""
from __future__ import annotations

import math

import pandas as pd


def _last(series: dict, n: int) -> list[float]:
    vals = [v for _, v in sorted(series.items())]
    return vals[-n:] if len(vals) >= n else []


def metrics(f: dict) -> dict:
    """Turn one company's yearly SEC series into the numbers the rules use."""
    ni3 = _last(f.get("net_income", {}), 3)
    cfo3 = _last(f.get("cfo", {}), 3)
    rev4 = _last(f.get("revenue", {}), 4)
    ni4 = _last(f.get("net_income", {}), 4)
    op3 = _last(f.get("operating_income", {}), 3)
    assets3 = _last(f.get("assets", {}), 3)
    cl3 = _last(f.get("current_liabilities", {}), 3)
    eq = _last(f.get("equity", {}), 1)
    last_year = max(f.get("net_income", {}) or [""])
    def latest(item):                      # a figure only counts if it is for the latest year
        s = f.get(item, {})
        return [s[last_year]] if last_year in s else []
    dn, dc = latest("debt_noncurrent"), latest("debt_current")
    debt = (dn or [0.0])[0] + (dc or [0.0])[0]
    interest = latest("interest_expense")
    debt_unknown = not dn and not dc and bool(interest) and interest[0] > 0   # pays interest but debt not found

    m = {"losses_3y": None, "debt_equity": None, "interest_cover": None, "cash_conversion_3y": None,
         "roce_floor_3y": None, "rev_growth": None, "profit_growth": None}
    if len(ni3) == 3:
        m["losses_3y"] = any(v < 0 for v in ni3)
    if eq and eq[0] > 0 and not debt_unknown:
        m["debt_equity"] = debt / eq[0]
    if interest and op3:
        m["interest_cover"] = op3[-1] / interest[0] if interest[0] > 0 else math.inf
    if len(cfo3) == 3 and len(ni3) == 3 and sum(ni3) > 0:
        m["cash_conversion_3y"] = sum(cfo3) / sum(ni3)
    if len(op3) == 3 and len(assets3) == 3 and len(cl3) == 3:
        roces = [o / (a - c) for o, a, c in zip(op3, assets3, cl3) if (a - c) > 0]
        if len(roces) == 3:
            m["roce_floor_3y"] = min(roces)

    def steady(v4):
        if len(v4) < 4 or v4[0] <= 0 or v4[-2] <= 0:
            return None
        one_year = v4[-1] / v4[-2] - 1
        cagr3 = (v4[-1] / v4[0]) ** (1 / 3) - 1 if v4[-1] > 0 else -1.0
        return min(one_year, cagr3)

    m["rev_growth"] = steady(rev4)
    m["profit_growth"] = steady(ni4)
    return m


def kill(m: dict, rules: dict) -> list[str]:
    why = []
    if m["losses_3y"] is None:
        why.append("profit history missing")
    elif m["losses_3y"]:
        why.append("loss in last 3 years")
    de = m["debt_equity"]
    if de is None:
        why.append("debt-to-equity missing")
    elif de > rules["max_debt_equity"]:
        why.append(f"debt-to-equity {de:.2f} > {rules['max_debt_equity']}")
    low_debt = de is not None and de < rules["near_zero_debt"]
    ic = m["interest_cover"]
    if not low_debt:
        if ic is None:
            why.append("interest cover missing")
        elif ic < rules["min_interest_cover"]:
            why.append(f"interest cover {ic:.1f}× < {rules['min_interest_cover']}×")
    cc = m["cash_conversion_3y"]
    if cc is None:
        why.append("cash-flow history missing")
    elif cc < rules["min_cash_conversion"]:
        why.append(f"cash conversion {cc:.2f} < {rules['min_cash_conversion']}")
    return why


def pct(s: pd.Series) -> pd.Series:
    return (s.rank(pct=True) * 100).fillna(0.0)


def shortlist(rows: list[dict], rules: dict, weights: dict, size: int) -> pd.DataFrame:
    """rows: [{ticker, ...metrics}] → survivors ranked on quality + growth; top `size` flagged."""
    df = pd.DataFrame(rows)
    df["reasons"] = df.apply(lambda r: kill(r.to_dict(), rules), axis=1)
    df["passed"] = df["reasons"].map(lambda w: not w)
    s = df[df["passed"]].copy()
    s["score_quality"] = (pct(s["roce_floor_3y"]) + pct(s["cash_conversion_3y"])) / 2
    s["score_growth"] = (pct(s["rev_growth"]) + pct(s["profit_growth"])) / 2
    wq, wg = weights["quality"], weights["growth"]
    s["score_qg"] = (s["score_quality"] * wq + s["score_growth"] * wg) / (wq + wg)
    s = s.sort_values("score_qg", ascending=False).reset_index(drop=True)
    s["qg_rank"] = range(1, len(s) + 1)
    s["shortlisted"] = s["qg_rank"] <= size
    return s
