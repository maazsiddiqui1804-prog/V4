"""V4 app (D-108, D-112) — phone-first, plain English. Home answers "what do I need to do?".
Read-only: never places orders (D-003). Simulated results are always labelled (CLAUDE.md rule 4).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v4 import app_logic as L  # noqa: E402

st.set_page_config(page_title="V4", page_icon="📊", layout="centered")
st.markdown("""<style>
  .block-container {padding-top: 3.5rem; padding-bottom: 3rem; max-width: 640px;}
  h1 {font-size: 1.6rem !important;} h3 {font-size: 1.1rem !important; margin-top: 1rem;}
  .small {color: #9aa0a6; font-size: 0.85rem;}
</style>""", unsafe_allow_html=True)

TODAY = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
C = L.cfg()


def card(c: dict):
    with st.container(border=True):
        st.markdown(f"**{c['title']}**  \n<span class='small'>{c['sub']}</span>", unsafe_allow_html=True)
        st.write(c["line"])
        st.write(c["action"])


def home():
    st.title(f"V4 · {TODAY:%a %-d %b}")
    st.subheader("To do now")
    items = L.todos(TODAY, c=C)
    if items:
        for i in items:
            st.checkbox(i, key=i)
        st.caption("Ticks are just for you — they reset when the page reloads.")
    else:
        st.success("Nothing to do right now.")
    st.subheader("Coming up")
    for when, what in L.coming_up(TODAY, c=C):
        st.markdown(f"**{when}** — {what}")
    st.subheader("How V4 is doing")
    for k, v in L.status(c=C).items():
        st.markdown(f"**{k}:** {v}")
    w = L.waiting(c=C)
    if w:
        st.subheader("Waiting on you (no rush)")
        for x in w:
            st.markdown(f"• {x}")


def india():
    st.title("India investing")
    st.write("Every month V4 ranks Nifty 500 companies on quality, growth and momentum, "
             "and tells you what to buy with that month's money. You place the orders in Kite.")
    label, cards = L.india_cards()
    if not cards:
        st.info("The first list arrives in December.")
        return
    st.caption(f"List for {label} — top 10")
    for c in cards:
        card(c)


def us():
    st.title("US investing")
    st.write("AI-related US companies (chips, software, hardware, power) picked on quality and growth. "
             "Each one is checked on Zerodha before prices are pulled. No US buys until you approve the numbers.")
    cards = L.us_cards()
    if not cards:
        st.info("Shortlist not built yet.")
        return
    for c in cards[:10]:
        card(c)
    if len(cards) > 10:
        with st.expander(f"Show all {len(cards)}"):
            for c in cards[10:]:
                card(c)


def trading():
    st.title("Trading")
    st.markdown("""**How it works (rules approved 10 Nov, D-137)**
- Buy a stock that closes at a **new 52-week high** on heavy volume, if it's already among the strongest 20%.
- Only when the overall market is healthy (Nifty 500 above its 200-day average).
- **Stop-loss** about two normal daily moves below the buy price — set it in Kite as a GTT.
- **Sell** the morning after it closes below its 50-day average. No profit target: winners are allowed to run.
- Risk 1% of the trading money per trade; at most 6 at a time.""")
    st.info(L.status(c=C)["Trading"] + ". Signals will appear here every evening once it starts.")
    s = L.trading_summary()
    if s:
        with st.expander("Past simulation (not real results)"):
            st.write(f"{s.get('period')}: {s.get('trades')} trades, average {s.get('avg_r', 0):+.2f} R per trade, "
                     f"{s.get('cagr', 0):.0%} a year, worst drop {s.get('max_drawdown', 0):.0%}.")
            st.caption("R = the amount risked on a trade. Simulations use today's Nifty 500 list, which flatters results.")


def more():
    st.title("More")
    st.subheader("Benchmarks")
    st.write("V4 must beat simply buying these index funds (lines start at 100).")
    bl = L.benchmark_lines()
    if bl.empty:
        st.caption("Benchmark chart unavailable.")
    else:
        st.line_chart(bl, height=260)
    st.subheader("Red flags")
    rf = L.q("SELECT f.detected_at AS date, s.symbol, f.flag_type AS flag FROM red_flags f "
             "JOIN securities s USING(security_id) ORDER BY f.detected_at DESC LIMIT 20")
    if rf.empty:
        st.write("None so far.")
    else:
        st.dataframe(rf, hide_index=True, use_container_width=True)
    st.caption("Data refreshes whenever the cloud jobs update the repo. Starting numbers are untested placeholders.")


PAGES = {"Home": home, "India": india, "US": us, "Trading": trading, "More": more}
choice = st.segmented_control("Page", list(PAGES), default="Home", label_visibility="collapsed") or "Home"
PAGES[choice]()
