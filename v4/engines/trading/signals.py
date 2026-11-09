"""Trading Engine signals (D-040–D-046). End-of-day data only.

Plain English, for each stock on each day (all numbers from config → trading):
- Liquid: 20-day average traded value ≥ ₹20 cr (D-040).
- Uptrend: 50-day average above 200-day average and close above the 50-day (D-042).
- Strong: 6-month return in the top 20% of the universe that day (relative strength).
- Breakout: close is the highest close of the last 20 days (today included, beating all 19 before)
  on volume ≥ 1.5× its 20-day average (D-042).
- Not overextended: close ≤ 10% above its 20-day average.
- Stop: 0.5% below the lowest low of the last 10 days; skipped if that's >10% below the close.
Signal fires at the close; entry is next morning (D-043).
Weak market (D-041): Nifty 500 below its 200-day average → half risk per trade.

Input frame columns: date, symbol, open, high, low, close, volume (adjusted for splits/bonuses).
"""
from __future__ import annotations

import pandas as pd


def indicators(px: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    px = px.sort_values(["symbol", "date"]).copy()
    g = px.groupby("symbol", group_keys=False)
    px["dma_fast"] = g["close"].transform(lambda s: s.rolling(cfg["trend_fast_dma"]).mean())
    px["dma_slow"] = g["close"].transform(lambda s: s.rolling(cfg["trend_slow_dma"]).mean())
    px["dma20"] = g["close"].transform(lambda s: s.rolling(20).mean())
    px["vol20"] = g["volume"].transform(lambda s: s.shift(1).rolling(20).mean())
    px["traded"] = px["close"] * px["volume"]
    px["value20_cr"] = px.groupby("symbol")["traded"].transform(lambda s: s.rolling(20).mean() / 1e7)
    n = cfg["breakout_days"]
    px["prior_high_close"] = g["close"].transform(lambda s: s.shift(1).rolling(n - 1).max())
    px["low_n"] = g["low"].transform(lambda s: s.rolling(cfg["stop_lookback_days"]).min())
    px["ret_rs"] = g["close"].transform(lambda s: s / s.shift(cfg["rs_lookback_days"]) - 1)
    px["rs_pct"] = px.groupby("date")["ret_rs"].rank(pct=True)
    return px


def signals(px: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Rows where every entry condition holds, with the proposed stop."""
    d = px
    cond = (
        (d["value20_cr"] >= cfg["liquidity_floor_cr_per_day"])
        & (d["dma_fast"] > d["dma_slow"]) & (d["close"] > d["dma_fast"])
        & (d["rs_pct"] >= 1 - cfg["rs_top_fraction"])
        & (d["close"] > d["prior_high_close"])
        & (d["volume"] >= cfg["volume_multiple"] * d["vol20"])
        & (d["close"] <= d["dma20"] * (1 + cfg["max_stretch_above_20dma"]))
    )
    s = d[cond].copy()
    s["stop"] = s["low_n"] * (1 - cfg["stop_buffer"])
    s = s[(s["close"] - s["stop"]) / s["close"] <= cfg["max_initial_risk"]]
    return s.sort_values(["date", "rs_pct"], ascending=[True, False])


def weak_market(index_close: pd.Series, slow: int = 200) -> pd.Series:
    """True on days the index closes below its 200-day average (D-041)."""
    return index_close < index_close.rolling(slow).mean()
