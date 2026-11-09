"""Daily India prices for the Trading Engine BACKTEST (D-130: no Kite Connect before the GMAT).

Plain English: downloads ~4 years of daily open/high/low/close/volume for today's Nifty 500
plus the Nifty 500 index from Yahoo Finance, adjusted for splits and bonuses so a 1:2 split
doesn't look like a crash. Saved as one compressed file (D-111: prices live in compressed
files, not the database). Live trading will switch to Kite Connect data (D-106) once it starts.
Run in the cloud:  python -m v4.importers.india_prices
"""
from __future__ import annotations

import sys

import pandas as pd

from v4.db import ROOT, connect, DB_PATH

OUT = ROOT / "data" / "prices" / "india_daily.csv.gz"
INDEX_OUT = ROOT / "data" / "prices" / "nifty500_index.csv"
INDEX_TICKER = "^CRSLDX"          # Nifty 500 on Yahoo


def universe(db_path=DB_PATH) -> pd.DataFrame:
    with connect(db_path) as c:
        return pd.read_sql("""SELECT s.symbol, s.sector FROM securities s
            JOIN universe_membership u USING(security_id)
            WHERE u.universe='NIFTY500' AND u.as_of=(SELECT MAX(as_of) FROM universe_membership WHERE universe='NIFTY500')""", c)


def tidy(raw: pd.DataFrame, yahoo_to_symbol: dict) -> pd.DataFrame:
    """yfinance multi-ticker frame (columns: (field, ticker)) → long rows."""
    long = raw.stack(level=1, future_stack=True).reset_index()
    long.columns = [str(c).lower() for c in long.columns]
    long = long.rename(columns={"ticker": "yahoo", "level_1": "yahoo"})
    long["symbol"] = long["yahoo"].map(yahoo_to_symbol)
    long = long.dropna(subset=["close"])
    return long[["date", "symbol", "open", "high", "low", "close", "volume"]]


def fetch(period: str = "4y", batch: int = 50) -> str:
    import yfinance as yf
    u = universe()
    ymap = {f"{s}.NS": s for s in u["symbol"]}
    parts, missing = [], []
    tickers = list(ymap)
    for i in range(0, len(tickers), batch):
        chunk = tickers[i:i + batch]
        raw = yf.download(chunk, period=period, auto_adjust=True, progress=False, group_by="column", threads=True)
        got = tidy(raw, ymap) if not raw.empty else pd.DataFrame()
        parts.append(got)
        missing += [ymap[t] for t in chunk if got.empty or ymap[t] not in set(got["symbol"])]
    px = pd.concat(parts, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    px.to_csv(OUT, index=False, float_format="%.4f", compression="gzip")
    idx = yf.download(INDEX_TICKER, period=period, auto_adjust=True, progress=False)
    close = idx["Close"].squeeze().rename("close")
    close.index.name = "date"
    close.to_csv(INDEX_OUT, float_format="%.2f")
    return (f"India prices: {px['symbol'].nunique()} of {len(u)} Nifty 500 stocks, "
            f"{px['date'].min()}→{px['date'].max()}, index {len(close)} days. "
            f"Missing: {', '.join(missing[:20])}{'…' if len(missing) > 20 else ''}")


def fix_unadjusted(px: pd.DataFrame, threshold: float = 0.30) -> tuple[pd.DataFrame, list]:
    """Yahoo sometimes misses a split/bonus/demerger (e.g. MOTILALOFS 1:4 on 2024-01-01 shows as -75%).
    Any overnight drop bigger than 30% is treated as a corporate action: earlier prices are scaled by
    the open/previous-close ratio (volumes the other way). Real 30% overnight crashes in Nifty 500
    stocks are rare; each fix is listed in the backtest report."""
    px = px.sort_values(["symbol", "date"]).reset_index(drop=True)
    fixes = []
    for sym, g in px.groupby("symbol"):
        ratio = g["open"] / g["close"].shift(1)
        for i in g.index[ratio < 1 - threshold]:          # splits, bonuses, demergers only push prices down
            r = ratio[i]
            earlier = g.index[g.index < i]
            px.loc[earlier, ["open", "high", "low", "close"]] *= r
            px.loc[earlier, "volume"] /= r
            fixes.append((sym, str(px.at[i, "date"])[:10], round(r - 1, 3)))
    return px, fixes


def load(fix: bool = True) -> tuple[pd.DataFrame, pd.Series]:
    px = pd.read_csv(OUT, parse_dates=["date"])
    if fix:
        px, _ = fix_unadjusted(px)
    idx = pd.read_csv(INDEX_OUT, parse_dates=["date"]).set_index("date")["close"]
    return px, idx


if __name__ == "__main__":
    print(fetch())
    sys.exit(0)
