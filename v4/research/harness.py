"""Strategy research harness (RESEARCH ONLY — results are historical simulation, never live).

Plain English:
- Prices are reshaped into date × stock grids so every rule is computed for all stocks at once.
- Breakout-style strategies are simulated trade by trade (each signal on its own), with the same
  fills as the engine: buy next morning's open + slippage, gap below stop fills at the open,
  round-trip costs charged. Result = list of trades with net R and % return.
- Momentum rotation (hold the top-N strongest stocks, re-pick monthly) is simulated as a portfolio.
- Periods are fixed in advance: TRAIN 2012–2019 (search), VALID 2020–2022 (confirm),
  HOLDOUT 2023–2026 (one final test, no tuning afterwards).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

PERIODS = {"train": ("2012-01-01", "2019-12-31"), "valid": ("2020-01-01", "2022-12-31"),
           "holdout": ("2023-01-01", "2026-12-31")}
SLIP = 0.001                       # each side
COST_RT = 0.0025 + 0.001           # ≈ STT/stamp/exchange/GST both sides + DP on a ~₹15k position


class Grid:
    def __init__(self, px: pd.DataFrame, index_close: pd.Series):
        w = {k: px.pivot(index="date", columns="symbol", values=k).sort_index() for k in
             ["open", "high", "low", "close", "volume"]}
        self.dates = w["close"].index
        self.symbols = w["close"].columns
        c = w["close"]
        self.close, self.open = c.values, w["open"].reindex_like(c).values
        self.high, self.low = w["high"].reindex_like(c).values, w["low"].reindex_like(c).values
        self.volume = w["volume"].reindex_like(c).values
        self.df = w
        idx = index_close.reindex(self.dates).ffill()
        self.index = idx.values
        self.mkt_up = (idx > idx.rolling(200).mean()).values
        self._cache: dict = {}

    def f(self, name: str) -> np.ndarray:
        """Cached features (date × stock arrays)."""
        if name in self._cache:
            return self._cache[name]
        c = self.df["close"]
        if name.startswith("dma"):
            v = c.rolling(int(name[3:]), min_periods=int(name[3:])).mean()
        elif name.startswith("hi"):                       # highest close of the previous N days
            n = int(name[2:])
            v = c.shift(1).rolling(n, min_periods=n).max()
        elif name.startswith("ll"):                       # lowest low of the last N days
            n = int(name[2:])
            v = self.df["low"].rolling(n, min_periods=n).min()
        elif name == "atr14":
            h, l, pc = self.df["high"], self.df["low"], c.shift(1)
            tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()]).groupby(level=0).max()
            v = tr.reindex(c.index).rolling(14).mean()
        elif name == "vol20":
            v = self.df["volume"].shift(1).rolling(20).mean()
        elif name == "liq_rank":                          # rank of 20-day traded value among stocks
            v = (c * self.df["volume"]).rolling(20).mean().rank(axis=1, pct=True)
        elif name.startswith("mom"):                      # N-day return, skipping the last 21 days when 'mom252s'
            n = int(name[3:].rstrip("s"))
            skip = 21 if name.endswith("s") else 0
            v = c.shift(skip) / c.shift(n) - 1
        elif name.startswith("rs"):
            v = self.f_df("mom" + name[2:]).rank(axis=1, pct=True)
        else:
            raise KeyError(name)
        arr = v.reindex_like(c).values.astype(np.float64)
        self._cache[name] = arr
        if name.startswith("mom"):
            self._cache["df_" + name] = v
        return arr

    def f_df(self, name: str) -> pd.DataFrame:
        self.f(name)
        return self._cache["df_" + name]


def entry_mask(g: Grid, breakout=20, vol_mult=1.5, trend=True, rs="126", rs_top=0.2,
               regime=False, liq=0.4, stretch=None) -> np.ndarray:
    c = g.close
    m = np.isfinite(c) & (g.f("liq_rank") >= liq)
    if breakout:
        m &= c > g.f(f"hi{breakout}")
    if vol_mult:
        m &= g.volume >= vol_mult * g.f("vol20")
    if trend:
        m &= (g.f("dma50") > g.f("dma200")) & (c > g.f("dma50"))
    if rs:
        m &= g.f(f"rs{rs}") >= 1 - rs_top
    if stretch:
        m &= c <= g.f("dma20") * (1 + stretch)
    if regime:
        m &= g.mkt_up[:, None]
    return np.nan_to_num(m, nan=0).astype(np.bool_)


@njit(cache=True)
def _simulate(mask, o, h, l, c, atr, ll, trail_ma, stop_kind, stop_k, max_risk, target_r,
              be_after_partial, trail_kind, trail_after_partial, chand_k, max_days, slip, cost_rt):
    T, N = c.shape
    out = []
    for n in range(N):
        t = 0
        while t < T - 2:
            if not mask[t, n] or not np.isfinite(o[t + 1]):
                t += 1
                continue
            e = o[t + 1, n] * (1 + slip)
            if stop_kind == 0:
                stop = c[t, n] - stop_k * atr[t, n]
            else:
                stop = ll[t, n] * 0.995
            risk = e - stop
            if not np.isfinite(risk) or risk <= 0 or risk / e > max_risk:
                t += 1
                continue
            left, partial, realized = 1.0, False, 0.0
            hi_close = c[t, n]
            exit_next = False
            d = t + 1
            exit_d = -1
            while d < T:
                if not np.isfinite(o[d, n]):
                    d += 1
                    continue
                if exit_next:
                    realized += left * (o[d, n] * (1 - slip) - e)
                    left = 0.0
                    exit_d = d
                    break
                if d > t + 1 and o[d, n] <= stop:
                    realized += left * (o[d, n] * (1 - slip) - e)
                    left = 0.0
                    exit_d = d
                    break
                if l[d, n] <= stop:
                    realized += left * (stop * (1 - slip) - e)
                    left = 0.0
                    exit_d = d
                    break
                if target_r > 0 and not partial and h[d, n] >= e + target_r * risk:
                    realized += 0.5 * (e + target_r * risk) * (1 - slip) - 0.5 * e
                    left = 0.5
                    partial = True
                    if be_after_partial:
                        stop = max(stop, e)
                hi_close = max(hi_close, c[d, n])
                active = (not trail_after_partial) or partial
                if active and trail_kind == 1 and c[d, n] < trail_ma[d, n]:
                    exit_next = True
                if active and trail_kind == 2:
                    stop = max(stop, hi_close - chand_k * atr[d, n])
                if d - t >= max_days:
                    exit_next = True
                d += 1
            if exit_d < 0:            # still open at the end of data: mark at last close
                exit_d = T - 1
                realized += left * (c[T - 1, n] - e)
            r_net = (realized - cost_rt * e) / risk
            out.append((t, n, exit_d, r_net, (realized - cost_rt * e) / e, exit_d - t, risk / e))
            t = exit_d
    return out


def simulate(g: Grid, mask, stop="atr", stop_k=2.0, max_risk=0.12, target_r=0.0, be=False,
             trail="ma", trail_ma=20, trail_after_partial=False, chand_k=3.0, max_days=60) -> pd.DataFrame:
    atr = g.f("atr14")
    ll = g.f("ll10")
    ma = g.f(f"dma{trail_ma}") if trail == "ma" else np.full_like(g.close, np.nan)
    res = _simulate(mask, g.open, g.high, g.low, g.close, atr, ll, ma,
                    0 if stop == "atr" else 1, stop_k, max_risk, target_r, be,
                    {"none": 0, "ma": 1, "chand": 2}[trail], trail_after_partial, chand_k, max_days, SLIP, COST_RT)
    if not res:
        return pd.DataFrame(columns=["date", "symbol", "exit", "r", "ret", "days", "risk_pct"])
    a = np.array(res)
    return pd.DataFrame({"date": g.dates[a[:, 0].astype(int)], "symbol": g.symbols[a[:, 1].astype(int)],
                         "exit": g.dates[a[:, 2].astype(int)], "r": a[:, 3], "ret": a[:, 4],
                         "days": a[:, 5].astype(int), "risk_pct": a[:, 6]})


def score(trades: pd.DataFrame, period: str) -> dict:
    a, b = PERIODS[period]
    t = trades[(trades["date"] >= a) & (trades["date"] <= b)]
    if len(t) == 0:
        return {"n": 0}
    yearly = t.groupby(t["date"].dt.year)["r"].mean()
    return {"n": len(t), "avg_r": t["r"].mean(), "med_r": t["r"].median(), "win": (t["r"] > 0).mean(),
            "avg_ret": t["ret"].mean(), "days": t["days"].mean(), "yrs_pos": (yearly > 0).mean(),
            "worst_yr_r": yearly.min()}


def portfolio(trades: pd.DataFrame, max_open=6, risk=0.01, start=None, end=None, capital=1.0) -> dict:
    """Fixed-fractional portfolio from a trade list: take signals in date order (strongest first is not
    known here, so ties keep file order), skip when max_open positions are already held."""
    t = trades.sort_values("date")
    if start:
        t = t[(t["date"] >= start) & (t["date"] <= end)]
    eq, peak, mdd = capital, capital, 0.0
    open_ = []                                 # (exit_date, pnl)
    curve = []
    for r in t.itertuples():
        open_.sort()
        while open_ and open_[0][0] <= r.date:
            ex, pnl = open_.pop(0)
            eq += pnl
            peak = max(peak, eq)
            mdd = min(mdd, eq / peak - 1)
            curve.append((ex, eq))
        if len(open_) >= max_open:
            continue
        size = min(eq * risk / r.risk_pct, eq / max_open * 2)     # cap any one position at 2× an equal slot
        open_.append((r.exit, size * r.ret))
    for ex, pnl in sorted(open_):
        eq += pnl
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
        curve.append((ex, eq))
    if not curve:
        return {"cagr": 0.0, "mdd": 0.0, "final": capital}
    years = max((pd.Timestamp(curve[-1][0]) - pd.Timestamp(t["date"].iloc[0])).days / 365.25, 0.5)
    return {"cagr": (eq / capital) ** (1 / years) - 1, "mdd": mdd, "final": eq}


def rotation(g: Grid, top=20, mom="252s", rebalance=21, regime=True, liq=0.4, start="2012-01-01",
             end="2026-12-31", cost=0.004) -> dict:
    """Hold the top-N stocks by momentum, equal weight, re-pick every `rebalance` days; when the market
    is below its 200-day average (regime=True) hold cash. Cost charged on the fraction of the
    portfolio replaced each time (round trip incl. slippage)."""
    c = g.df["close"]
    ret = c.pct_change().fillna(0.0).values
    score_ = g.f(f"mom{mom}")
    liq_ok = g.f("liq_rank") >= liq
    d0 = g.dates.searchsorted(pd.Timestamp(start))
    d1 = g.dates.searchsorted(pd.Timestamp(end), side="right")
    hold = np.zeros(len(g.symbols), dtype=bool)
    eq, curve = 1.0, []
    for d in range(max(d0, 260), d1):
        if (d - d0) % rebalance == 0:
            if regime and not g.mkt_up[d - 1]:
                new = np.zeros_like(hold)
            else:
                s = np.where(liq_ok[d - 1] & np.isfinite(score_[d - 1]), score_[d - 1], -np.inf)
                k = min(top, int(np.isfinite(s).sum()))
                new = np.zeros_like(hold)
                if k:
                    new[np.argsort(-s)[:k]] = True
            changed = (hold ^ new).sum() / (2 * top) if (hold.any() or new.any()) else 0.0
            eq *= 1 - cost * changed
            hold = new
        if hold.any():
            r = np.nanmean(np.where(hold, ret[d], np.nan))
            eq *= 1 + (0.0 if not np.isfinite(r) else r)
        curve.append((g.dates[d], eq))
    s = pd.Series(dict(curve))
    years = (s.index[-1] - s.index[0]).days / 365.25
    return {"cagr": s.iloc[-1] ** (1 / years) - 1, "mdd": (s / s.cummax() - 1).min(), "curve": s}


def buy_hold_index(g: Grid, start: str, end: str) -> dict:
    s = pd.Series(g.index, index=g.dates)[start:end].dropna()
    years = (s.index[-1] - s.index[0]).days / 365.25
    return {"cagr": (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1, "mdd": (s / s.cummax() - 1).min()}
