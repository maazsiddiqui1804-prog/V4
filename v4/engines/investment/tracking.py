"""Forward-tracking of frozen monthly lists (D-063) — the evidence for India investing reviews.

Plain English: every month's ranked list is frozen. From the freeze date we follow every stock on it,
whether you bought it or not, and compare it with the Nifty 500 over the same days. That answers:
- does the ranking work at all (top 20 vs the index, at 1 and 3 years)?
- which part of the score predicts returns (top third vs bottom third on quality, growth, momentum)?
- does the valuation guardrail help (buyable vs "too expensive" names)?
Results are facts for the January review; nothing here changes a rule (D-066).
"""
from __future__ import annotations

import pandas as pd

PARTS = {"score_quality": "Quality", "score_growth": "Growth", "score_momentum": "Momentum", "score_total": "Overall score"}


def price_on(series: pd.Series, day) -> float | None:
    """Close on `day`, or the last close before it."""
    s = series[series.index <= pd.Timestamp(day)]
    return float(s.iloc[-1]) if len(s) else None


def track(lists: pd.DataFrame, px: pd.DataFrame, index_close: pd.Series) -> pd.DataFrame:
    """lists: list_month, symbol, rank, score_*, passes_guardrail, frozen_at (frozen rows only).
    px: date, symbol, close (adjusted). Returns one row per list stock with return and excess vs Nifty 500."""
    if lists.empty or px.empty:
        return pd.DataFrame()
    closes = {s: g.set_index("date")["close"].sort_index() for s, g in px.groupby("symbol")}
    idx = index_close.sort_index()
    today = px["date"].max()
    rows = []
    for r in lists.itertuples():
        start = pd.Timestamp(str(r.frozen_at)[:10])
        s = closes.get(r.symbol)
        p0, p1 = (price_on(s, start), price_on(s, today)) if s is not None else (None, None)
        i0, i1 = price_on(idx, start), price_on(idx, today)
        ret = p1 / p0 - 1 if p0 and p1 else None
        iret = i1 / i0 - 1 if i0 and i1 else None
        rows.append({"list_month": r.list_month, "symbol": r.symbol, "rank": r.rank,
                     **{k: getattr(r, k, None) for k in PARTS},
                     "buyable": bool(r.passes_guardrail), "frozen": start.date().isoformat(),
                     "days": (today - start).days, "return": ret, "nifty500": iret,
                     "excess": (ret - iret) if ret is not None and iret is not None else None})
    return pd.DataFrame(rows)


def ranking_check(t: pd.DataFrame, top: int = 20) -> pd.DataFrame:
    """Per list: average return of its top N vs the Nifty 500 over the same days."""
    if t.empty:
        return t
    g = t[t["rank"] <= top].dropna(subset=["return"]).groupby("list_month")
    return pd.DataFrame({"Days since freeze": g["days"].max(), f"Top {top} return": g["return"].mean(),
                         "Nifty 500": g["nifty500"].mean(), "Ahead of index": g["excess"].mean()}).reset_index() \
        .rename(columns={"list_month": "List"})


def factor_check(t: pd.DataFrame) -> pd.DataFrame:
    """For each score part: excess return of the top third minus the bottom third (pooled across lists).
    Positive = that part of the score picked better stocks."""
    t = t.dropna(subset=["excess"])
    out = []
    for col, name in PARTS.items():
        d = t.dropna(subset=[col])
        if len(d) < 9 or d[col].nunique() < 3:          # no spread in that score part → nothing to compare
            continue
        third = d.groupby("list_month")[col].transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=False))
        hi, lo = d[third == 2]["excess"].mean(), d[third == 0]["excess"].mean()
        out.append({"Score part": name, "Top third vs index": hi, "Bottom third vs index": lo, "Gap": hi - lo,
                    "Stocks": len(d)})
    return pd.DataFrame(out)


def guardrail_check(t: pd.DataFrame) -> pd.DataFrame:
    t = t.dropna(subset=["excess"])
    if t.empty:
        return t
    g = t.groupby("buyable")["excess"].agg(["mean", "count"]).reset_index()
    g["Names"] = g["buyable"].map({True: "Buyable (price under limit)", False: "Too expensive (skipped)"})
    return g.rename(columns={"mean": "Ahead of index", "count": "Stocks"})[["Names", "Ahead of index", "Stocks"]]
