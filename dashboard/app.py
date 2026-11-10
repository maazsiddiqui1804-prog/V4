"""Investing & Trading — Maaz's V4 app (D-108, D-112). Phone-first, plain English, interactive.
Pages: India Investing · India Trading · US Investing · Analysis · Build.
Read-only for markets: never places orders (D-003). Simulated results are always labelled (CLAUDE.md rule 4).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v4 import app_logic as L  # noqa: E402

APP_NAME = "Investing & Trading"
st.set_page_config(page_title=APP_NAME, page_icon="📈", layout="centered")
st.markdown("""<style>
  .block-container {padding-top: 3.2rem; padding-bottom: 3rem; max-width: 720px;}
  h1 {font-size: 1.5rem !important;} h2 {font-size: 1.2rem !important;} h3 {font-size: 1.05rem !important;}
</style>""", unsafe_allow_html=True)

TODAY = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
C = L.cfg()
SIM = "Simulation — not real results"


# ---------------------------------------------------------------- shared helpers
@st.cache_data(ttl=3600)
def benchmark_lines():
    return L.benchmark_lines()


@st.cache_data(ttl=1800)
def load_series():
    return L.series()


def secret_token():
    try:
        return st.secrets.get("GITHUB_TOKEN")
    except Exception:
        return None


def todo_box(items: list[str], key: str):
    """To-dos with ticks that persist when a GitHub key is set in Streamlit secrets (else only this visit)."""
    if not items:
        return
    done = st.session_state.setdefault("done", L.load_done())
    for i in items:
        ticked = st.checkbox(i, value=bool(done.get(i)), key=f"{key}:{i}")
        if ticked != bool(done.get(i)):
            done[i] = TODAY.isoformat() if ticked else None
            token = secret_token()
            if token and L.save_done({k: v for k, v in done.items() if v}, token):
                st.toast("Saved")
            elif not token:
                st.toast("Ticked for this visit only — see the Build page to make ticks stick")


def stock_chart(symbol: str, lines: dict | None = None):
    s = load_series()
    d = s[s["symbol"] == symbol][["date", "close"]] if not s.empty else pd.DataFrame()
    if d.empty:
        st.caption(f"No price history for {symbol} yet — it appears after the next daily refresh.")
        return
    d = d.sort_values("date").copy()
    d["50-day average"] = d["close"].rolling(50).mean()
    base = alt.Chart(d).encode(x=alt.X("date:T", title=None))
    layers = [base.mark_line(color="#4c8bf5").encode(
                  y=alt.Y("close:Q", title="₹", scale=alt.Scale(zero=False)),
                  tooltip=[alt.Tooltip("date:T"), alt.Tooltip("close:Q", format=",.2f")]),
              base.mark_line(color="#f5a623", strokeDash=[4, 3]).encode(y="50-day average:Q")]
    for label, val in (lines or {}).items():
        if val is not None and pd.notna(val):
            rule = pd.DataFrame({"y": [float(val)], "label": [f"{label} ₹{float(val):,.0f}"]})
            colour = "#e5534b" if "stop" in label.lower() else "#57ab5a"
            layers.append(alt.Chart(rule).mark_rule(strokeDash=[2, 2], color=colour).encode(y="y:Q", tooltip="label:N"))
    st.altair_chart(alt.layer(*layers).properties(height=240), use_container_width=True)
    keys = " · ".join(f"{k} ₹{float(v):,.2f}" for k, v in (lines or {}).items() if v is not None and pd.notna(v))
    st.caption("Blue = price · orange dashes = 50-day average" + (f" · {keys}" if keys else ""))


def pick(df: pd.DataFrame, key: str, height: int | None = None):
    """Table where tapping a row selects it. Returns the selected row (or None)."""
    kw = {"height": height} if height else {}
    ev = st.dataframe(df, hide_index=True, use_container_width=True, on_select="rerun",
                      selection_mode="single-row", key=key, **kw)
    rows = ev.selection.rows if ev is not None and hasattr(ev, "selection") else []
    return df.iloc[rows[0]] if rows else None


def bench_chart(names: list[str], height=240):
    bl = benchmark_lines()
    cols = [c for c in names if c in bl.columns]
    if bl.empty or not cols:
        st.caption("Benchmark data not available yet.")
        return
    d = bl[cols].rename_axis("date").reset_index().melt("date", var_name="Benchmark", value_name="Value")
    st.altair_chart(alt.Chart(d).mark_line().encode(
        x=alt.X("date:T", title=None), y=alt.Y("Value:Q", title="Start = 100", scale=alt.Scale(zero=False)),
        color=alt.Color("Benchmark:N", legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Benchmark", "date:T", alt.Tooltip("Value:Q", format=".1f")]).properties(height=height),
        use_container_width=True)


def holdings_section(h: pd.DataFrame, key: str, buy_below: dict | None = None):
    if h.empty:
        st.info("No holdings yet.")
        return
    tot_inv, tot_val = h["invested"].sum(), h["value"].sum()
    c = st.columns(3)
    c[0].metric("Invested", f"₹{tot_inv:,.0f}")
    c[1].metric("Worth now", f"₹{tot_val:,.0f}")
    c[2].metric("Gain", f"{tot_val / tot_inv - 1:+.1%}")
    sectors = sorted(h["sector"].dropna().unique())
    chosen = st.multiselect("Filter by sector", sectors, key=f"{key}-sec") if len(sectors) > 1 else []
    v = h[h["sector"].isin(chosen)] if chosen else h
    t = pd.DataFrame({"Stock": v["symbol"], "Shares": v["quantity"].astype(int), "Bought at (₹)": v["avg_price"].round(2),
                      "Price now (₹)": v["price"].round(2), "Worth (₹)": v["value"].round(0),
                      "Gain %": (v["gain_pct"] * 100).round(1), "Sector": v["sector"]})
    st.caption("Tap a row for its chart.")
    row = pick(t, key)
    if row is not None:
        stock_chart(row["Stock"], {"Bought at": row["Bought at (₹)"], "Buy below": (buy_below or {}).get(row["Stock"])})


# ---------------------------------------------------------------- pages
def india_investing():
    st.title("India Investing")
    st.caption("Monthly: V4 ranks Nifty 500 companies on quality, growth and momentum and builds the buy list. "
               "You place limit orders in Kite.")
    items = L.todos(TODAY, c=C)
    if items:
        st.markdown("**To do now**")
        todo_box(items, "in")

    st.header("1 · What to buy")
    amount = st.number_input("Money to invest this month (₹)", min_value=0, step=5000,
                             value=int(C["investment"]["portfolio"]["monthly_amount_inr"]),
                             help="Change it to see the plan for a different amount. The standing default stays ₹25,000.")
    res = L.india_plan(float(amount), c=C)
    if res is None:
        st.info("The first buy list arrives in December (after the GMAT). It will show here: stock, shares, "
                "the most to pay (limit price), amount — and this box will recalculate it for any amount you type.")
    else:
        orders, notes, month = res
        st.caption(f"List for {month} · prices from the last close")
        if orders.empty:
            st.write("Nothing to buy at today's prices.")
        else:
            st.dataframe(orders, hide_index=True, use_container_width=True)
        for n in notes:
            st.caption(n)
        lst = L.india_list()
        with st.expander("Full ranked list (tap a row for its chart)"):
            f = st.multiselect("Sector", sorted(lst["Sector"].dropna().unique()), key="in-list-sec")
            only = st.toggle("Only buyable now", key="in-list-buy")
            v = lst[lst["Sector"].isin(f)] if f else lst
            v = v[v["Buyable now"]] if only else v
            row = pick(v, "in-list", height=320)
            if row is not None:
                stock_chart(row["Stock"], {"Buy below": row["Buy below (₹)"]})
    plan = L.latest_plan()
    if plan and any(x["action"] != "HOLD" for x in plan.get("holdings", [])):
        st.subheader("Sell / trim / review")
        for x in plan["holdings"]:
            if x["action"] != "HOLD":
                st.write(f"**{x['action'].title()} {x['symbol']}** — {x['reason']}")

    st.header("2 · Your portfolio")
    h = L.india_holdings()
    lst = L.india_list()
    holdings_section(h, "in-hold", dict(zip(lst.get("Stock", []), lst.get("Buy below (₹)", []))))

    st.header("3 · Against the benchmarks")
    st.caption("V4 has to beat simply buying these index funds. Lines start at 100.")
    bench_chart(["Nifty 500", "Quality 30", "Momentum 30"])

    st.header("4 · Quick read")
    bl = benchmark_lines()
    if not bl.empty:
        r = bl.ffill().iloc[-1] / bl.bfill().iloc[0] - 1
        st.write(f"• Since {bl.index[0]:%b %Y}: Nifty 500 {r.get('Nifty 500', 0):+.1%}, "
                 f"Quality 30 {r.get('Quality 30', 0):+.1%}, Momentum 30 {r.get('Momentum 30', 0):+.1%}.")
    if h.empty:
        st.write("• No money invested yet — first buys in December.")
    else:
        hs = h.sort_values("gain_pct")
        st.write(f"• {len(h)} stocks. Best: {hs.iloc[-1].symbol} {hs.iloc[-1].gain_pct:+.0%}. "
                 f"Worst: {hs.iloc[0].symbol} {hs.iloc[0].gain_pct:+.0%}.")


def india_trading():
    st.title("India Trading")
    t = L.trading_today()
    st.caption("Rules (D-137): buy a new 52-week high on heavy volume among the strongest 20%, only when the market "
               "is healthy · stop-loss ≈ 2 normal daily moves below · sell the morning after a close below the "
               "50-day average · 1% risk per trade, max 6 open.")
    st.warning("WATCH-ONLY until paper trading starts after the GMAT. Nothing here is a real or paper position.")

    st.header("1 · Today's signals")
    if not t:
        st.info("Signals appear after the first daily refresh (weekdays ~6:15 PM).")
    else:
        st.caption(f"From the close of {t['date']}" + (" · market weak: no new trades" if t.get("weak_market") else ""))
        new = pd.DataFrame(t.get("new", []))
        if new.empty:
            st.write("No new breakouts today.")
        else:
            show = pd.DataFrame({"Stock": new["symbol"], "Sector": new["sector"], "Entry ≈ (₹)": new["ref_close"],
                                 "Stop-loss (₹)": new["stop"], "Shares": new["qty"], "Risk (₹)": new["risk_inr"]})
            st.caption("Entry = buy at the next open (today's close shown as a guide). No profit target — exit when it "
                       "closes below its 50-day average. Tap a row for its chart.")
            row = pick(show, "tr-new")
            if row is not None:
                stock_chart(row["Stock"], {"Entry ≈": row["Entry ≈ (₹)"], "Stop-loss": row["Stop-loss (₹)"]})
        wl = pd.DataFrame(t.get("watchlist", []))
        if not wl.empty:
            st.subheader("Close to breaking out")
            st.caption("A close above the trigger on heavy volume makes it a signal. Set Kite price alerts at the trigger.")
            row = pick(wl.rename(columns={"symbol": "Stock", "trigger": "Trigger (₹)"}), "tr-watch")
            if row is not None:
                stock_chart(row["Stock"], {"Trigger": row["Trigger (₹)"]})
        if t.get("skipped"):
            st.caption("Skipped: " + ", ".join(f"{s} ({w})" for s, w in t["skipped"][:8]))

    st.header("2 · Positions")
    if C["trading"].get("paper_start"):
        holdings_section(L.india_holdings(engine="trading"), "tr-hold")
    else:
        st.info("Paper trading starts after the GMAT. Open positions, stop-losses and exits will show here.")

    st.header("3 · Against the benchmark")
    eq = L.DATA / "backtest" / "equity.csv"
    s = L.trading_summary()
    if eq.exists():
        e = pd.read_csv(eq, index_col=0, parse_dates=True).iloc[:, 0]
        e = e[e != e.iloc[0]].combine_first(e.iloc[:1]) if (e != e.iloc[0]).any() else e
        start = e.index[0]
        d = pd.DataFrame({"Trading rules (sim)": e / e.iloc[0] * 100})
        ix = L.nifty500()
        if not ix.empty and (ix.index >= start).any():
            ix2 = ix[ix.index >= start]
            d = d.join((ix2 / ix2.iloc[0] * 100).rename("Nifty 500"), how="outer").ffill()
        d = d.rename_axis("date").reset_index().melt("date", var_name="Line", value_name="Value")
        st.caption(f"{SIM}: the trading rules on past prices vs the Nifty 500 (both start at 100).")
        st.altair_chart(alt.Chart(d).mark_line().encode(
            x=alt.X("date:T", title=None), y=alt.Y("Value:Q", title="Start = 100", scale=alt.Scale(zero=False)),
            color=alt.Color("Line:N", legend=alt.Legend(orient="bottom", title=None))).properties(height=240),
            use_container_width=True)

    st.header("4 · Quick read")
    if s:
        st.write(f"• {SIM} ({s.get('period')}): {s.get('trades')} trades, average {s.get('avg_r', 0):+.2f}R each, "
                 f"{s.get('win_rate', 0):.0%} winners, {s.get('cagr', 0):.0%} a year, worst drop {s.get('max_drawdown', 0):.0%}.")
    st.write("• Most trades lose a little; a few big winners pay for them — that's why there's no profit target.")
    st.write("• Go-live bar: paper trading must average at least 0.3R over 30+ trades and 3+ months (D-048).")


def us_investing():
    st.title("US Investing")
    st.caption("AI-related US companies (chips, software & cloud, hardware & networking, power), picked on quality "
               "and growth, checked on Zerodha, then ranked with price momentum.")
    st.header("1 · What to buy")
    if not C["us"].get("approved"):
        st.info("No US buys yet. Waiting for: the Kite check of the shortlist, your approval of the US numbers, "
                "and the W-8BEN form. The buy list — stock, shares, most to pay — will show here.")
    s = L.us_shortlist()
    if not s.empty:
        st.subheader(f"Shortlist ({len(s)})")
        c1, c2 = st.columns(2)
        areas = c1.multiselect("Area", sorted(s["Area"].unique()), key="us-area")
        sort = c2.selectbox("Sort by", ["Rank", "Quality", "Growth", "Sales growth", "Profit growth"], key="us-sort")
        v = s[s["Area"].isin(areas)] if areas else s
        v = v.sort_values(sort, ascending=(sort == "Rank"))
        st.caption("Scores are out of 100 against the other US candidates. Tap a row for details.")
        row = pick(v[["Rank", "Ticker", "Company", "Area", "Quality", "Growth", "On Zerodha"]], "us-short", height=360)
        if row is not None:
            r = s[s["Ticker"] == row["Ticker"]].iloc[0]
            with st.container(border=True):
                st.markdown(f"**{r['Company']} ({r['Ticker']})** — {r['Area']}")
                c = st.columns(2)
                c[0].metric("Return on capital (worst yr)", f"{r['ROCE (worst of 3 yrs)']:.0f}%")
                c[1].metric("Debt / equity", f"{r['Debt/equity']:.2f}")
                c = st.columns(2)
                c[0].metric("Sales growth", f"{r['Sales growth']:.0f}%")
                c[1].metric("Profit growth", f"{r['Profit growth']:.0f}%")
                st.caption(f"Reports in {r['Reports in']}. Growth = the lower of last year and the 3-year average. "
                           "Price chart arrives once it's confirmed on Zerodha.")
    st.header("2 · Your portfolio")
    st.info("No US holdings yet.")
    st.header("3 · Against the benchmark")
    st.caption("Nasdaq-100 index funds in rupees (start = 100) — the bar the US picks have to beat.")
    bench_chart(["Nasdaq-100", "Nifty 500"])
    st.header("4 · Quick read")
    if not s.empty:
        st.write("• Shortlist mix: " + ", ".join(f"{k} {n}" for k, n in s["Area"].value_counts().items()) + ".")
        st.write(f"• {int((s['On Zerodha'] == '✅ Yes').sum())} of {len(s)} confirmed on Zerodha so far.")
    st.write("• Tax and remittance safeguards (TCS, Schedule FA, estate-tax warning, W-8BEN) are built in (D-132).")


def analysis():
    st.title("Analysis")
    st.caption("Everything V4 suggested, what you took, what you skipped, and how each turned out.")
    sug = L.suggestions()
    st.header("Suggestions: taken vs skipped")
    if sug.empty:
        st.info("This fills in from December, after the first buy list. Every suggestion is tracked whether you "
                "buy it or not, so you can see what skipping cost or saved.")
    else:
        months = sorted(sug["Month"].unique())
        c1, c2 = st.columns(2)
        rng = (c1.select_slider("Months", months, value=(months[0], months[-1])) if len(months) > 1
               else (months[0], months[0]))
        which = c2.radio("Show", ["All", "Taken", "Skipped"], horizontal=True)
        v = sug[(sug["Month"] >= rng[0]) & (sug["Month"] <= rng[1])]
        v = v if which == "All" else v[v["Taken"] == (which == "Taken")]
        v2 = v.assign(Status=v["Taken"].map({True: "Taken", False: "Skipped"}), Change=(v["Since suggestion"] * 100).round(1))
        g = v2.groupby("Status")["Change"].mean()
        c = st.columns(2)
        c[0].metric("Taken — average since suggested", f"{g['Taken']:+.1f}%" if "Taken" in g else "—")
        c[1].metric("Skipped — average since suggested", f"{g['Skipped']:+.1f}%" if "Skipped" in g else "—")
        st.altair_chart(alt.Chart(v2).mark_bar().encode(
            x=alt.X("Change:Q", title="% since suggestion"), y=alt.Y("Stock:N", sort="-x", title=None),
            color=alt.Color("Status:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Month", "Stock", "Status", alt.Tooltip("Change:Q", format="+.1f")])
            .properties(height=max(160, 22 * len(v2))), use_container_width=True)
        row = pick(v2[["Month", "Stock", "Status", "Suggested at (₹)", "Price now (₹)", "Change"]], "an-sug")
        if row is not None:
            stock_chart(row["Stock"], {"Suggested at": row["Suggested at (₹)"]})

    st.header("Overall portfolio")
    h = L.india_holdings()
    if h.empty:
        st.info("No holdings yet. Once you buy, this shows value, gain by stock, and the split by sector and market.")
    else:
        c = st.columns(2)
        by_sec = h.groupby("sector")["value"].sum().reset_index()
        c[0].altair_chart(alt.Chart(by_sec).mark_arc(innerRadius=40).encode(
            theta="value:Q", color=alt.Color("sector:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["sector", alt.Tooltip("value:Q", format=",.0f")]).properties(height=240), use_container_width=True)
        c[1].altair_chart(alt.Chart(h.assign(g=h["gain_pct"] * 100)).mark_bar().encode(
            x=alt.X("g:Q", title="Gain %"), y=alt.Y("symbol:N", sort="-x", title=None),
            color=alt.condition("datum.g >= 0", alt.value("#57ab5a"), alt.value("#e5534b"))).properties(height=240),
            use_container_width=True)

    st.header("Trading rules — simulation, not real results")
    tr = L.DATA / "backtest" / "trades.csv"
    if tr.exists():
        t = pd.read_csv(tr)
        reasons = t["exit_reason"].value_counts().rename_axis("How it ended").reset_index(name="Trades")
        reasons["Avg result (R)"] = reasons["How it ended"].map(t.groupby("exit_reason")["r"].mean()).round(2)
        st.dataframe(reasons, hide_index=True, use_container_width=True)
        st.altair_chart(alt.Chart(t).mark_bar().encode(
            x=alt.X("r:Q", bin=alt.Bin(step=0.5), title="Result per trade (R)"), y=alt.Y("count()", title="Trades"))
            .properties(height=200), use_container_width=True)
        st.caption("R = the amount risked on a trade. Many small losses, a few large wins.")


def build_page():
    st.title("Build")
    b = L.build()
    st.caption(f"Where V4's build is. Copy of the V4 Dashboard on claude.ai — updated {b.get('updated', '?')}.")
    for p in b.get("phases", []):
        st.markdown(f"**{p['name']}** — {p['status']}")
        st.progress(p["pct"] / 100)

    st.header("Waiting on you")
    tasks = pd.DataFrame(b.get("tasks", []))
    items = L.todos(TODAY, c=C) + L.waiting(c=C)
    if not tasks.empty:
        mine = tasks[(tasks["owner"] == "Maaz") & (tasks["status"] != "Done")]
        items += [f"{r.task_id}: {r.task}" for r in mine.itertuples()]
    items = list(dict.fromkeys(items))
    if items:
        todo_box(items, "build")
    else:
        st.success("Nothing waiting on you.")

    st.header("Coming up")
    for when, what in L.coming_up(TODAY, c=C):
        st.markdown(f"**{when}** — {what}")

    st.header("Cloud jobs")
    j = L.jobs()
    if j.get("jobs"):
        jd = pd.DataFrame(j["jobs"]).rename(columns={"job": "Job", "last_run": "Last run (UTC)", "result": "Result"})
        jd["Result"] = jd["Result"].map(lambda r: {"success": "✅ ok", "failure": "❌ failed"}.get(r, r))
        st.dataframe(jd, hide_index=True, use_container_width=True)
    else:
        st.caption("Job status appears after the first daily refresh.")

    st.header("All tasks")
    if not tasks.empty:
        c1, c2 = st.columns(2)
        own = c1.multiselect("Owner", sorted(tasks["owner"].dropna().unique()), key="b-own")
        sts = c2.multiselect("Status", sorted(tasks["status"].dropna().unique()), key="b-st")
        v = tasks[tasks["owner"].isin(own)] if own else tasks
        v = v[v["status"].isin(sts)] if sts else v
        st.dataframe(v.rename(columns={"task_id": "ID", "phase": "Phase", "owner": "Owner", "status": "Status",
                                       "task": "Task"})[["ID", "Phase", "Owner", "Status", "Task"]],
                     hide_index=True, use_container_width=True, height=360)
    with st.expander("Make to-do ticks stick (optional, 3 min)"):
        st.markdown("Right now ticks last only for your visit. To save them: on GitHub create a **fine-grained token** "
                    "for repository **V4** only, with **Contents: Read and write**. Then in this app open "
                    "**Manage app → Settings → Secrets** and add `GITHUB_TOKEN = \"...\"`. Ask Claude to walk you through it.")


pages = [st.Page(india_investing, title="India Investing", icon="🇮🇳", default=True, url_path="india-investing"),
         st.Page(india_trading, title="India Trading", icon="📈", url_path="india-trading"),
         st.Page(us_investing, title="US Investing", icon="🇺🇸", url_path="us-investing"),
         st.Page(analysis, title="Analysis", icon="📊", url_path="analysis"),
         st.Page(build_page, title="Build", icon="🛠️", url_path="build")]
NAV = {"🇮🇳 India Invest": pages[0], "📈 India Trade": pages[1], "🇺🇸 US Invest": pages[2],
       "📊 Analysis": pages[3], "🛠️ Build": pages[4]}
current = st.navigation(pages, position="hidden")
here = next(k for k, v in NAV.items() if v.url_path == current.url_path)
st.markdown(f"<div style='font-weight:800;font-size:1.45rem;line-height:1.2;margin:-0.6rem 0 0.6rem 0'>"
            f"{APP_NAME}</div>", unsafe_allow_html=True)
go = st.segmented_control("Section", list(NAV), default=here, label_visibility="collapsed", key=f"nav-{here}")
if go and go != here:
    st.switch_page(NAV[go])
current.run()
