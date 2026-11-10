"""Trading Engine signals — rules "B2" (D-137, from the 2026-11 strategy search). End-of-day data only.

Plain English, for each stock on each day (all numbers from config → trading):
- Liquid: 20-day average traded value ≥ ₹20 cr (D-040).
- Uptrend: 50-day average above 200-day average and close above the 50-day (D-042).
- Strong: 12-month return (skipping the latest month) in the top 20% of the universe that day.
- Breakout: close above the highest close of the previous 250 days (a 52-week high),
  on volume ≥ 1.5× its 20-day average.
- Stop: signal close − 2 × the 14-day average true range (typical daily move); skipped if >15% below.
- Market filter: no new trades while the Nifty 500 is below its 200-day average.
Signal fires at the close; entry is next morning (D-043).
Exits (backtest/daily): stop, or a close below the 50-day average (sell next morning), or ~1 year.

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
    td = cfg.get("trail_dma", 20)
    px["dma_trail"] = g["close"].transform(lambda s: s.rolling(td).mean())
    prev = g["close"].shift(1)
    tr = pd.concat([px["high"] - px["low"], (px["high"] - prev).abs(), (px["low"] - prev).abs()], axis=1).max(axis=1)
    px["atr14"] = tr.groupby(px["symbol"]).transform(lambda s: s.rolling(14).mean())
    px["vol20"] = g["volume"].transform(lambda s: s.shift(1).rolling(20).mean())
    px["traded"] = px["close"] * px["volume"]
    px["value20_cr"] = px.groupby("symbol")["traded"].transform(lambda s: s.rolling(20).mean() / 1e7)
    n = cfg["breakout_days"]
    px["prior_high_close"] = g["close"].transform(lambda s: s.shift(1).rolling(n).max())
    px["low_n"] = g["low"].transform(lambda s: s.rolling(cfg["stop_lookback_days"]).min())
    skip = cfg.get("rs_skip_days", 0)
    px["ret_rs"] = g["close"].transform(lambda s: s.shift(skip) / s.shift(cfg["rs_lookback_days"]) - 1)
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
    )
    if cfg.get("max_stretch_above_20dma") is not None:
        cond &= d["close"] <= d["dma20"] * (1 + cfg["max_stretch_above_20dma"])
    s = d[cond].copy()
    if cfg.get("stop_method", "lowest_low") == "atr":
        s["stop"] = s["close"] - cfg["stop_atr_multiple"] * s["atr14"]
    else:
        s["stop"] = s["low_n"] * (1 - cfg["stop_buffer"])
    s = s[(s["close"] - s["stop"]) / s["close"] <= cfg["max_initial_risk"]]
    return s.sort_values(["date", "rs_pct"], ascending=[True, False])


def weak_market(index_close: pd.Series, slow: int = 200) -> pd.Series:
    """True on days the index closes below its 200-day average (D-041)."""
    return index_close < index_close.rolling(slow).mean()
