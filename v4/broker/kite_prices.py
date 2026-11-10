"""Daily prices from Kite Connect (replaces Yahoo once Kite is on, D-080/D-106). Read-only."""
from __future__ import annotations

import csv
import datetime as dt
import io
import time

import pandas as pd

INDEX_SYMBOL = "NIFTY 500"


def tokens(instruments_csv: str, symbols: set[str]) -> tuple[dict[str, int], int | None]:
    """NSE equity tradingsymbol → instrument_token for our symbols, plus the Nifty 500 index token."""
    out, idx = {}, None
    for r in csv.DictReader(io.StringIO(instruments_csv)):
        if r.get("segment") == "INDICES" and r.get("tradingsymbol") == INDEX_SYMBOL:
            idx = int(r["instrument_token"])
        elif r.get("instrument_type") == "EQ" and r.get("tradingsymbol") in symbols:
            out[r["tradingsymbol"]] = int(r["instrument_token"])
    return out, idx


def recent(k, symbols: list[str], days: int = 14, pause: float = 0.35) -> tuple[pd.DataFrame, pd.Series, list]:
    """Last `days` daily candles for each symbol and the Nifty 500 (≈3 requests/second, Kite's limit)."""
    tok, idx_tok = tokens(k.instruments("NSE"), set(symbols))
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    rows, missing = [], [s for s in symbols if s not in tok]
    for sym, t in tok.items():
        for c in k.historical(t, f"{start} 00:00:00", f"{end} 23:59:59").get("candles", []):
            rows.append({"date": pd.Timestamp(c[0][:10]), "symbol": sym, "open": c[1], "high": c[2],
                         "low": c[3], "close": c[4], "volume": c[5]})
        time.sleep(pause)
    idx = pd.Series(dtype=float)
    if idx_tok:
        cs = k.historical(idx_tok, f"{start} 00:00:00", f"{end} 23:59:59").get("candles", [])
        idx = pd.Series({pd.Timestamp(c[0][:10]): c[4] for c in cs}, name="close")
    return pd.DataFrame(rows), idx, missing
