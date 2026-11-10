"""V4 dashboard (D-108, D-112). Streamlit Community Cloud, private app, reads this repo's data files.

Two views: Action (default) — what to do now; Analysis — how things are going.
Read-only: the dashboard never places orders and never writes data (D-003).
Simulated results (backtest, paper) are always labelled as such (CLAUDE.md rule 4).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from statistics import median

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"

st.set_page_config(page_title="V4", page_icon="📊", layout="wide")


# ---------- loaders (pure functions so tests can call them) ----------
def q(sql: str, params=()) -> pd.DataFrame:
    p = DATA / "v4.sqlite"
    if not p.exists():
        return pd.DataFrame()
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as c:
        try:
            return pd.read_sql(sql, c, params=params)
        except Exception:
            return pd.DataFrame()


def csv(path: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(path, **kw) if path.exists() else pd.DataFrame()


def latest_brief() -> tuple[str, str] | None:
    files = sorted((DATA / "briefs").glob("*.md")) if (DATA / "briefs").exists() else []
    return (files[-1].stem, files[-1].read_text()) if files else None


def latest_list() -> pd.DataFrame:
    return q("""SELECT l.list_month, l.rank, s.symbol, s.name, s.sector, ROUND(l.score_total,1) AS score,
                ROUND(l.buy_below,2) AS buy_below, l.passes_guardrail, l.regime, l.frozen_at
                FROM investment_lists l JOIN securities s USING(security_id)
                WHERE l.list_month=(SELECT MAX(list_month) FROM investment_lists) ORDER BY l.rank""")


def holdings() -> pd.DataFrame:
    return q("""SELECT h.snapshot_date, s.market, s.symbol, s.sector, h.engine, h.quantity, h.avg_price,
                ROUND(h.quantity*h.avg_price) AS cost
                FROM holdings_snapshots h JOIN securities s USING(security_id)
                WHERE h.snapshot_date=(SELECT MAX(snapshot_date) FROM holdings_snapshots)""")


def red_flags() -> pd.DataFrame:
    return q("""SELECT f.detected_at, s.symbol, f.flag_type, f.reviewed, f.source_url
                FROM red_flags f JOIN securities s USING(security_id) ORDER BY f.detected_at DESC LIMIT 50""")


def benchmark_lines() -> pd.DataFrame:
    """D-122: chained median daily return of each benchmark's index funds, from data/benchmarks/navs.csv."""
    navs = csv(DATA / "benchmarks" / "navs.csv")
    if navs.empty:
        return navs
    out = {}
    for bench, g in navs.sort_values("date").groupby("benchmark"):
        last, level, line = {}, 100.0, {}
        for date, day in g.groupby("date"):
            rets = [r.nav / last[r.scheme_code] - 1 for r in day.itertuples() if last.get(r.scheme_code)]
            if rets:
                level *= 1 + median(rets)
            line[date] = level
            for r in day.itertuples():
                last[r.scheme_code] = r.nav
        out[bench] = line
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def backtest() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    d = DATA / "backtest"
    summ = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else {}
    curve = csv(d / "equity.csv", index_col=0, parse_dates=True)
    return summ, curve, csv(d / "trades.csv")


# ---------- views ----------
def action_view():
    st.header("Action")
    st.caption("What to do now. V4 never places orders — you decide and act in Kite.")
    b = latest_brief()
    st.subheader("India + US investing — monthly brief")
    if b:
        st.markdown(f"**{b[0]}**")
        st.code(b[1], language=None)
    else:
        st.info("No brief yet. The first real brief is December 2026 (after the GMAT, D-129).")
    lst = latest_list()
    if not lst.empty:
        st.markdown(f"**Ranked list {lst.list_month.iloc[0]}** "
                    f"({'frozen' if lst.frozen_at.notna().all() else 'preview, not frozen'}) — "
                    "✅ = buyable now (price below buy-below and PEG check passed)")
        show = lst.head(20).assign(buyable=lst.passes_guardrail.map({1: "✅", 0: "❌"}))
        st.dataframe(show[["rank", "symbol", "name", "sector", "score", "buy_below", "buyable"]],
                     hide_index=True, use_container_width=True)
    st.subheader("US (AI sleeve)")
    rank = csv(DATA / "us" / "ranking.csv")
    short = csv(DATA / "us" / "shortlist.csv")
    if not rank.empty:
        st.dataframe(rank.head(10), hide_index=True, use_container_width=True)
    elif not short.empty:
        need = short[short.get("zerodha_checked", pd.Series(dtype=str)).fillna("") == ""]
        st.info(f"Shortlist of {len(short)} ready; Kite check pending for {len(need)} names (T-057). "
                "No US orders until the US numbers are approved (T-054).")
        cols = [c for c in ["qg_rank", "ticker", "name", "layer", "score_quality", "score_growth", "zerodha_checked"]
                if c in short]
        st.dataframe(short[cols].round(1), hide_index=True, use_container_width=True)
    else:
        st.info("US shortlist not built yet.")
    st.subheader("Trading")
    st.info("Paper trading starts after the GMAT with Kite Connect (D-130). Signals will appear here: "
            "entry, stop-loss (place as GTT, D-110), quantity, and exits (close below the 50-day average, D-137).")


def analysis_view():
    st.header("Analysis")
    st.subheader("Benchmarks (index-fund median, D-122)")
    bl = benchmark_lines()
    if not bl.empty:
        st.line_chart(bl, height=280)
        st.caption("Each line starts at 100 on its first day. Nifty 500 and Quality 30 are the 3-year kill-test bars; "
                   "Momentum 30 is diagnostic only (D-107).")
    st.subheader("Holdings")
    h = holdings()
    if h.empty:
        st.info("No holdings yet (account is V4-only and empty until the first buys).")
    else:
        st.dataframe(h, hide_index=True, use_container_width=True)
    st.subheader("Red flags (filings)")
    rf = red_flags()
    if rf.empty:
        st.caption("None recorded.")
    else:
        st.dataframe(rf, hide_index=True, use_container_width=True)
    st.subheader("Trading backtest — HISTORICAL SIMULATION, NOT LIVE")
    summ, curve, trades = backtest()
    if summ:
        c = st.columns(5)
        c[0].metric("Trades", summ.get("trades"))
        c[1].metric("Avg R (net)", f"{summ.get('avg_r', 0):.2f}")
        c[2].metric("Win rate", f"{summ.get('win_rate', 0):.0%}")
        c[3].metric("Return / yr", f"{summ.get('cagr', 0):.1%}")
        c[4].metric("Worst drawdown", f"{summ.get('max_drawdown', 0):.0%}")
        st.caption(f"{summ.get('period')} · today's Nifty 500 list applied to the past (flatters results) · "
                   "go-live bar D-048 needs ≥30 paper trades at ≥0.3R.")
        if not curve.empty:
            st.line_chart(curve, height=240)
        if not trades.empty:
            with st.expander("Backtest trades"):
                st.dataframe(trades, hide_index=True, use_container_width=True)
    else:
        st.caption("No backtest run yet.")
    st.subheader("US universe")
    u = csv(DATA / "us_universe.csv")
    if not u.empty:
        st.write(f"{len(u)} names · " + " · ".join(f"{k}: {v}" for k, v in u.layer.value_counts().items()))


def main():
    st.title("📊 V4")
    view = st.radio("View", ["Action", "Analysis"], horizontal=True, label_visibility="collapsed")
    if view == "Action":
        action_view()
    else:
        analysis_view()
    st.divider()
    st.caption("Starting numbers are untested placeholders. Data refreshes when the cloud jobs commit to the repo.")


main()
