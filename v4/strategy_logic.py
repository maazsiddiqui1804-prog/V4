"""Strategy & Philosophy page: why each bucket exists, its rules (read live from config), how it's doing
against its own target, and diagnostics that show WHERE it is going wrong — so reviews fix the right rule.
Reviews: quarterly = fixes only; January = strategy (D-066). Read-only; never places orders (D-003).
"""
from __future__ import annotations

import pandas as pd

from v4 import app_logic as L

BUCKETS = ["India Investing", "India Trading", "US Investing"]


def overall() -> list[str]:
    return [
        "**Purpose:** beat simply buying index funds while spending little time — or switch V4 off (D-010).",
        "**Target:** beat the benchmark by at least 2% a year after costs and tax over rolling 5 years, "
        "with no deeper falls than the benchmark (D-011, D-093).",
        "**Split:** starts at 90% investing / 10% trading and can move to **70/30** as trading proves itself live: "
        "20% after 50 live trades averaging ≥ 0.3R, up to 30% after 100; it steps back down if results fade. "
        "US is at most 30% of the investing part (D-088, D-089, D-100).",
        "**Who does what:** V4 screens, scores and signals; you decide and place every order. It never trades (D-003, D-015).",
        "**Discipline:** follow the signals; any override needs a reason and is scored later (D-016). "
        "Rules change only at reviews — quarterly for fixes, January for strategy, never mid-slump (D-066).",
        "**Evidence first:** strategies are chosen by what made money in tests, not by what we think should work (D-137).",
    ]


def philosophy(c: dict) -> dict[str, dict]:
    inv, tr, us = c["investment"], c["trading"], c["us"]
    kf = inv["kill_filters"]
    w = inv["score_weights"]
    return {
        "India Investing": {
            "why": "Own 15 strong Indian businesses for 3+ years. Quality first, growth second, momentum to avoid "
                   "buying while the market is dumping a stock; valuation only as a guardrail so we don't overpay (D-015, D-024, D-099).",
            "rules": [
                "Universe: Nifty 500 minus banks, NBFCs and insurers (D-021).",
                f"Kill filters: no losses in the last 2 years or trailing 12 months; debt/equity ≤ {kf['max_debt_equity']}; "
                f"interest cover ≥ {kf['min_interest_cover']}×; promoter pledge ≤ {kf['max_promoter_pledge_pct']}%; "
                f"cash conversion ≥ {kf['min_cash_conversion']} (D-023, D-116, D-123). Missing data = fail.",
                f"Score: quality {w['normal']['quality']} / growth {w['normal']['growth']} / momentum {w['normal']['momentum']}; "
                f"weak market {w['weak_market']['quality']}/{w['weak_market']['growth']}/{w['weak_market']['momentum']} (D-099, D-103, D-124).",
                f"Guardrail: buy only below price × (10-yr P/E × {1 + inv['valuation']['india_pe_margin']:.1f}) ÷ P/E, "
                f"and P/E-to-growth ≤ {inv['valuation']['india_max_peg']} (D-125).",
                f"Monthly: ₹{inv['portfolio']['monthly_amount_inr']:,} into 2–5 names, ≥ ₹{inv['min_buy_inr']:,} each, "
                f"until {inv['portfolio']['target_holdings']} holdings; ≤ 3 per sector while filling (D-105, D-126).",
                "Sell: fails a kill filter, red-flag filing, quality in the bottom quarter, or ranked below 100 for 2 months; "
                "trim above 2× target weight (D-027, D-127).",
            ],
            "target": "Beat Nifty 500 by ≥ 2%/yr (5-yr rolling); at 3 years must beat both Nifty 500 and Quality 30 index funds or switch to index funds (D-011, D-064).",
        },
        "India Trading": {
            "why": "Capture strong trends in Indian stocks with small, controlled risk per trade. Most trades lose "
                   "a little; a few big winners pay for everything — so cut losers fast and let winners run (D-137).",
            "rules": [
                f"Buy: close above the highest close of the last {tr['breakout_days']} days (52-week high) on ≥ "
                f"{tr['volume_multiple']}× normal volume, in an uptrend (50-day avg > 200-day avg), among the top "
                f"{tr['rs_top_fraction']:.0%} for 12-month strength, liquid (≥ ₹{tr['liquidity_floor_cr_per_day']} cr/day).",
                "Market filter: no new trades while the Nifty 500 is below its 200-day average.",
                f"Stop-loss: {tr['stop_atr_multiple']:g} × the stock's typical daily move below the signal close (skip if > "
                f"{tr['max_initial_risk']:.0%} away). Place it as a GTT the moment you buy (D-110).",
                f"Exit: the morning after a close below the {tr['trail_dma']}-day average; at most ~{tr['time_stop_days']} trading days.",
                f"Size: risk {tr['risk_per_trade']:.0%} of trading money per trade; max {tr['max_open']} open, "
                f"{tr['max_per_sector']} per sector; pause after a {tr['drawdown_brake_pct']}% fall until the next quarter (D-044, D-046, D-104).",
            ],
            "target": "Go-live bar: paper trading ≥ 3 months, ≥ 30 trades, average ≥ +0.3R after costs (D-048). Live, it starts with 10% of V4 "
                      "and earns up to 30%: 20% after 50 live trades at ≥ 0.3R, 30% after 100 (D-100).",
        },
        "US Investing": {
            "why": "Get AI exposure India can't offer yet: the chips, software, hardware and power companies building "
                   "AI — but only financially strong ones, and never overpaying for growth (D-017, D-022, D-101).",
            "rules": [
                "Universe: US companies in AI-chain industries (by official SEC industry code), worth ≥ $10B, available on Zerodha (D-133, D-134).",
                f"Kill filters: same as India (no losses in 3 yrs, debt/equity ≤ {us['kill_filters']['max_debt_equity']}, "
                f"interest cover, cash conversion ≥ {us['kill_filters']['min_cash_conversion']}).",
                f"Shortlist top {us['shortlist_size']} on quality + growth from SEC filings; check each on Zerodha; then rank "
                f"with price momentum ({us['weights']['quality']}/{us['weights']['growth']}/{us['weights']['momentum']}) (D-135, D-136).",
                f"Guardrail: P/E-to-growth ≤ {us['max_peg']} (D-101). If nothing passes for {us['fallback_months']} months, "
                "money goes to a Nasdaq-100 index fund (D-102).",
                f"Size: {us['target_holdings']} holdings; US ≤ 30% of investing (D-089). Tax safeguards built in (D-132).",
            ],
            "target": "Beat Nasdaq-100 index funds in rupees after costs, forex and tax (D-095).",
        },
    }


def scorecard(bucket: str, c: dict) -> list[tuple[str, str, str]]:
    """(measure, now, verdict) rows."""
    if bucket == "India Trading":
        s = L.trading_summary()
        live = c["trading"].get("paper_start")
        rows = [("Paper trading", f"since {live}" if live else "not started (after the GMAT)", "⏳")]
        if s:
            rows.append(("Average per trade (simulation)", f"{s.get('avg_r', 0):+.2f}R over {s.get('trades')} trades",
                         "✅ above 0.3R" if s.get("avg_r", 0) >= 0.3 else "⚠️ below the 0.3R bar"))
            rows.append(("Return / worst fall (simulation)", f"{s.get('cagr', 0):.0%}/yr · {s.get('max_drawdown', 0):.0%}", "ℹ️"))
        return rows
    if bucket == "India Investing":
        h = L.india_holdings()
        if h.empty:
            return [("Invested", "nothing yet — first buys in December", "⏳"),
                    ("vs Nifty 500 / Quality 30", "starts with the first buys", "⏳")]
        gain = h["value"].sum() / h["invested"].sum() - 1
        return [("Invested", f"₹{h['invested'].sum():,.0f} in {len(h)} stocks", "ℹ️"), ("Gain so far", f"{gain:+.1%}", "ℹ️")]
    s = L.us_shortlist()
    ok = int((s["On Zerodha"] == "✅ Yes").sum()) if not s.empty else 0
    return [("US holdings", "none yet", "⏳"), ("Shortlist confirmed on Zerodha", f"{ok} of {len(s)}", "⏳"),
            ("US numbers approved", "yes" if c["us"].get("approved") else "not yet (T-054)", "⏳")]


# ---------------------------------------------------------------- diagnostics
def trade_sources(c: dict) -> dict[str, pd.DataFrame]:
    """Trade lists available for diagnosis: simulation now; paper/live once they exist."""
    out = {}
    p = L.DATA / "backtest" / "trades.csv"
    if p.exists():
        t = pd.read_csv(p, parse_dates=["entry_date", "exit_date"])
        out["Simulation (past prices)"] = t
    for name, f in [("Paper", "paper_trades.csv"), ("Live", "live_trades.csv")]:
        q = L.DATA / "app" / f
        if q.exists():
            out[name] = pd.read_csv(q, parse_dates=["entry_date", "exit_date"])
    return out


DIMENSIONS = {"How it ended": "exit_reason", "Year": "year", "Sector": "sector", "Days held": "held_bucket",
              "Stop distance": "stop_bucket", "Market": "market"}


def enrich(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["year"] = t["entry_date"].dt.year.astype(str)
    t["held_bucket"] = pd.cut(t["days"], [-1, 5, 20, 60, 120, 10_000],
                              labels=["≤1 wk", "1–4 wks", "1–3 mths", "3–6 mths", "6+ mths"]).astype(str)
    stop_pct = (t["entry"] - t["stop"]) / t["entry"]
    t["stop_bucket"] = pd.cut(stop_pct, [0, 0.04, 0.07, 0.10, 1], labels=["<4%", "4–7%", "7–10%", "10%+"]).astype(str)
    t["market"] = t["weak_market"].map({True: "Weak market", False: "Healthy market"})
    return t


def breakdown(t: pd.DataFrame, dim: str) -> pd.DataFrame:
    g = t.groupby(DIMENSIONS[dim])
    out = pd.DataFrame({"Trades": g.size(), "Avg R": g["r"].mean().round(2), "Win rate": (g["r"].apply(lambda r: (r > 0).mean()) * 100).round(0),
                        "Total R": g["r"].sum().round(1)}).reset_index().rename(columns={DIMENSIONS[dim]: dim})
    return out.sort_values("Total R")


def rule_checks(t: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Each trading rule, the evidence, and whether it looks healthy. (check, evidence, verdict)"""
    out = []
    n = len(t)
    if not n:
        return out
    stops = t[t["exit_reason"].str.contains("stop")]
    gaps = t[t["exit_reason"].str.contains("gap")]
    wins, losses = t[t["r"] > 0], t[t["r"] <= 0]
    top = t["r"].nlargest(max(1, n // 10)).sum()
    out.append(("Average result per trade", f"{t['r'].mean():+.2f}R over {n} trades",
                "✅ meets 0.3R bar" if t["r"].mean() >= 0.3 and n >= 30 else "⚠️ below the go-live bar"))
    out.append(("Stop-losses hold at about −1R", f"{len(stops)} stopped, average {stops['r'].mean():+.2f}R" if len(stops) else "none",
                "✅" if not len(stops) or stops["r"].mean() > -1.2 else "⚠️ losses bigger than planned (gaps/slippage)"))
    out.append(("Overnight gaps below the stop", f"{len(gaps)} trades, average {gaps['r'].mean():+.2f}R" if len(gaps) else "none",
                "✅ rare" if len(gaps) <= 0.05 * n else "⚠️ frequent — consider smaller size"))
    out.append(("Winners pay for losers", f"avg win {wins['r'].mean():+.2f}R vs avg loss {losses['r'].mean():+.2f}R; "
                f"the best 10% of trades made {top:+.1f}R; all trades together {t['r'].sum():+.1f}R" if len(wins) and len(losses) else "—",
                "✅" if len(wins) and wins["r"].mean() > 2 * abs(losses["r"].mean()) else "⚠️ winners too small vs losers"))
    if t["weak_market"].any():
        wk = t[t["weak_market"]]
        out.append(("Weak-market trades", f"{len(wk)} trades, average {wk['r'].mean():+.2f}R",
                    "✅" if wk["r"].mean() > 0 else "⚠️ losing — the market filter should block these"))
    yearly = t.groupby(t["entry_date"].dt.year)["r"].mean()
    out.append(("Consistency across years", ", ".join(f"{y}: {v:+.2f}R" for y, v in yearly.items()),
                "✅ positive every year" if (yearly > 0).all() else f"⚠️ negative in {int((yearly <= 0).sum())} year(s)"))
    return out


def reason_label(w: str) -> str:
    if "missing" in w:
        return "Data missing: " + w.replace(" missing", "")
    for key, label in [("loss", "Made a loss in the last 3 years"), ("debt-to-equity", "Too much debt"),
                       ("interest cover", "Interest cover too low"), ("cash conversion", "Profits not turning into cash")]:
        if w.startswith(key):
            return label
    return w


def us_funnel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """How many US companies survive each step, and why the rest were cut."""
    from v4.engines.us import score as us
    uni = L.DATA / "us_universe.csv"
    met = L.DATA / "us" / "metrics.csv"
    rows, reasons = [], pd.DataFrame()
    if uni.exists():
        rows.append(("AI-industry US companies ≥ $10B", len(pd.read_csv(uni))))
    if met.exists():
        m = pd.read_csv(met)
        rules = L.cfg()["us"]["kill_filters"]
        num = ["debt_equity", "interest_cover", "cash_conversion_3y", "roce_floor_3y", "rev_growth", "profit_growth"]
        for col in num:
            m[col] = pd.to_numeric(m[col], errors="coerce")
        m["losses_3y"] = m["losses_3y"].map({True: True, False: False, "True": True, "False": False})
        why = m.apply(lambda r: us.kill({k: (None if pd.isna(v) else v) for k, v in r.items()}, rules), axis=1)
        rows.append(("Financials read from SEC", len(m)))
        rows.append(("Pass the kill filters", int((why.map(len) == 0).sum())))
        # one main reason per company (the first rule it fails: losses are checked first), so counts add up
        reasons = pd.Series([reason_label(ws[0]) for ws in why if ws]).value_counts() \
            .rename_axis("Main reason cut").reset_index(name="Companies")
    s = L.us_shortlist()
    if not s.empty:
        rows.append(("Shortlisted (top on quality + growth)", len(s)))
        rows.append(("Confirmed on Zerodha", int((s["On Zerodha"] == "✅ Yes").sum())))
    rows.append(("Bought", 0))
    return pd.DataFrame(rows, columns=["Step", "Companies"]), reasons
