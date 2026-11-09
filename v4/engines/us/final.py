"""US final ranking for the shortlist (D-099, D-101, D-102, D-136).

Plain English, only for shortlisted names that passed the Kite check (D-135):
- Momentum: average rank of 6- and 12-month price returns (same as India, D-124).
- Final score: quality/growth/momentum at 40/30/30 (D-099).
- Guardrail (D-101, US only): P/E vs growth. PEG = P/E ÷ (3-year EPS growth in %).
  Buy only if 0 < PEG ≤ the cap. No own-history P/E check for US.
- Fallback (D-102): if no US stock passes the guardrail for 3 months in a row,
  that month's US money goes to a Nasdaq-100 index fund instead.
"""
from __future__ import annotations

import pandas as pd


def pct(s: pd.Series) -> pd.Series:
    return (s.rank(pct=True) * 100).fillna(0.0)


def returns(closes: list[tuple[str, float]]) -> dict:
    """closes: [(date, close)] ascending, ~13 months. 6m ≈ 126 and 12m ≈ 252 trading days."""
    px = [c for _, c in closes]
    out = {"price": px[-1] if px else None, "ret_6m": None, "ret_12m": None}
    if len(px) > 126:
        out["ret_6m"] = px[-1] / px[-127] - 1
    if len(px) > 252:
        out["ret_12m"] = px[-1] / px[-253] - 1
    return out


def eps_growth_3y(eps: dict) -> float | None:
    v = [x for _, x in sorted(eps.items())][-4:]
    if len(v) < 4 or v[0] <= 0 or v[-1] <= 0:
        return None
    return (v[-1] / v[0]) ** (1 / 3) - 1


def rank(short: pd.DataFrame, weights: dict, max_peg: float) -> pd.DataFrame:
    """short: shortlisted rows with score_quality, score_growth, price, ret_6m, ret_12m, eps, eps_g3."""
    df = short.copy()
    df["score_momentum"] = (pct(df["ret_6m"]) + pct(df["ret_12m"])) / 2
    w = weights
    df["score_total"] = (df["score_quality"] * w["quality"] + df["score_growth"] * w["growth"]
                         + df["score_momentum"] * w["momentum"]) / (w["quality"] + w["growth"] + w["momentum"])
    df["pe"] = (df["price"] / df["eps"]).where(df["eps"] > 0)
    df["peg"] = (df["pe"] / (df["eps_g3"] * 100)).where(df["eps_g3"] > 0)
    df["passes_guardrail"] = (df["peg"] > 0) & (df["peg"] <= max_peg)
    df["guardrail_reason"] = df.apply(
        lambda r: "" if r.passes_guardrail else
        ("no positive P/E or EPS growth" if pd.isna(r.peg) else f"PEG {r.peg:.1f} > {max_peg}"), axis=1)
    df = df.sort_values("score_total", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df


def fallback_due(history: list[bool], months: int) -> bool:
    """history: per past month (oldest→newest), True if ANY US stock passed the guardrail."""
    recent = history[-months:]
    return len(recent) == months and not any(recent)
