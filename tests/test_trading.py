"""Checks Trading Engine signals, costs and the backtest mechanics on made-up prices."""
import numpy as np
import pandas as pd
import pytest
import yaml

from v4.db import ROOT
from v4.engines.trading import backtest as bt, costs, signals as sg

B2 = yaml.safe_load((ROOT / "config" / "placeholders.yaml").read_text())["trading"]
# The old rules (pre D-137) — kept to test the engine's partial-profit / time-stop / half-size mechanics.
CFG = dict(B2, rs_lookback_days=126, rs_skip_days=0, breakout_days=19, max_stretch_above_20dma=0.10,
           stop_method="lowest_low", max_initial_risk=0.10, partial_at_r=2.0, trail_dma=20,
           trail_after_partial=True, time_stop_days=20, weak_market_action="half_size")
DAYS = pd.bdate_range("2024-01-01", periods=320)


def frame(symbol, closes, vols=None, lows=None):
    closes = np.asarray(closes, float)
    vols = np.full(len(closes), 3e6) if vols is None else np.asarray(vols, float)
    lows = closes * 0.99 if lows is None else np.asarray(lows, float)
    return pd.DataFrame({"date": DAYS[:len(closes)], "symbol": symbol, "open": closes, "high": closes * 1.01,
                         "low": lows, "close": closes, "volume": vols})


def universe(leader_closes, leader_vols):
    parts = [frame("LEAD", leader_closes, leader_vols)]
    for i in range(4):
        parts.append(frame(f"FLAT{i}", 100 + np.sin(np.arange(320) / 7 + i)))
    return pd.concat(parts, ignore_index=True)


def leader(breakout_day=260, after=None):
    c = np.r_[np.linspace(80, 120, 240), np.full(breakout_day - 240, 119.0)]   # trend, then a 20-day base
    c = np.r_[c, [123.0]]                                                      # breakout close
    tail = after if after is not None else np.linspace(124, 140, 320 - len(c))
    c = np.r_[c, tail][:320]
    v = np.full(320, 3e6)
    v[breakout_day] = 6e6
    return c, v


def test_costs_match_zerodha_sheet():
    assert costs.buy_cost(100_000) == pytest.approx(100 + 3.07 + 0.1 + 15 + (3.07 + 0.1) * 0.18, abs=0.01)
    assert costs.sell_cost(100_000) == pytest.approx(100 + 3.17 + 3.17 * 0.18 + 15.34, abs=0.01)


def test_breakout_signal_fires_only_on_breakout_day():
    c, v = leader()
    s = sg.signals(sg.indicators(universe(c, v), CFG), CFG)
    lead = s[s.symbol == "LEAD"]
    assert list(lead.date) == [DAYS[260]]
    assert lead.stop.iloc[0] < 123 and (123 - lead.stop.iloc[0]) / 123 <= CFG["max_initial_risk"]


def test_no_signal_without_volume():
    c, v = leader()
    v[260] = 3e6
    s = sg.signals(sg.indicators(universe(c, v), CFG), CFG)
    assert (s.symbol == "LEAD").sum() == 0


def test_backtest_winner_takes_half_at_2r_and_enters_next_morning():
    c, v = leader(after=np.linspace(124, 170, 59))
    idx = pd.Series(np.linspace(100, 200, 320), index=DAYS)            # strong market
    res = bt.run(universe(c, v), idx, {"LEAD": "Tech"}, CFG)
    t = res["trades"]
    assert res["open_at_end"] == 0
    assert len(t) == 1 and t.entry_date.iloc[0] == str(DAYS[261].date())
    assert t.r.iloc[0] > 1 and not t.weak_market.iloc[0] and t.exit_reason.iloc[0] == "time stop"


def test_slow_winner_exits_on_time_stop_below_2r():
    c, v = leader()                                                    # drifts up too slowly to reach 2R in 20 days
    t = bt.run(universe(c, v), pd.Series(np.linspace(100, 200, 320), index=DAYS), {}, CFG)["trades"].iloc[0]
    assert t.exit_reason == "time stop" and 0 < t.r < 1 and t.days == 20


def test_backtest_gap_below_stop_fills_at_open():
    after = np.r_[[122.0, 100.0], np.full(57, 100.0)]                    # gaps far below the stop
    c, v = leader(after=after)
    idx = pd.Series(np.linspace(100, 200, 320), index=DAYS)
    res = bt.run(universe(c, v), idx, {"LEAD": "Tech"}, CFG)
    t = res["trades"].iloc[0]
    assert t.exit_reason == "gap below stop" and t.r < -1                # worse than 1R: gap loss
    assert bt.summary(res, CFG["capital_inr"])["trades"] == 1


def test_weak_market_halves_risk():
    c, v = leader()
    strong = bt.run(universe(c, v), pd.Series(np.linspace(100, 200, 320), index=DAYS), {}, CFG)["trades"]
    weak = bt.run(universe(c, v), pd.Series(np.linspace(200, 100, 320), index=DAYS), {}, CFG)["trades"]
    assert weak.weak_market.iloc[0] and weak.qty.iloc[0] == pytest.approx(strong.qty.iloc[0] / 2, abs=1)


def test_tidy_yahoo_frame():
    from v4.importers.india_prices import tidy
    cols = pd.MultiIndex.from_product([["Close", "High", "Low", "Open", "Volume"], ["TCS.NS", "INFY.NS"]],
                                      names=["Price", "Ticker"])
    raw = pd.DataFrame(np.arange(20.0).reshape(2, 10), index=pd.DatetimeIndex(DAYS[:2], name="Date"), columns=cols)
    raw.loc[DAYS[1], ("Close", "INFY.NS")] = np.nan                 # missing day is dropped
    out = tidy(raw, {"TCS.NS": "TCS", "INFY.NS": "INFY"})
    assert list(out.columns) == ["date", "symbol", "open", "high", "low", "close", "volume"]
    assert len(out) == 3 and set(out.symbol) == {"TCS", "INFY"}
    assert out[(out.symbol == "TCS") & (out.date == DAYS[0])].close.iloc[0] == 0.0


def test_evening_plan_new_signal_watch_and_exits():
    from v4.engines.trading import daily
    c, v = leader()
    px = universe(c, v)
    px = px[px.date <= DAYS[260]]                                       # evening of the breakout day
    idx = pd.Series(np.linspace(100, 200, 261), index=DAYS[:261])
    held = [daily.Open("FLAT0", "Misc", 98.0, 90.0, 10, 10, False, 19)]  # 20th day → time stop
    plan = daily.evening_plan(px, idx, {"LEAD": "Tech"}, held, 100_000, CFG)
    assert [n["symbol"] for n in plan["new"]] == ["LEAD"]
    n = plan["new"][0]
    assert n["risk_inr"] <= 1_000 and n["target_2r"] > n["ref_close"]
    assert ("FLAT0", "EXIT") == plan["actions"][0][:2] and "time stop" in plan["actions"][0][2]
    assert "LEAD" in daily.render(plan)


def test_evening_plan_watchlist_day_before_breakout():
    from v4.engines.trading import daily
    c, v = leader()
    c[255:260] = 118.6                                                   # sits 0.3% under its 20-day high
    px = universe(c, v)
    px = px[px.date <= DAYS[259]]
    idx = pd.Series(np.linspace(100, 200, 260), index=DAYS[:260])
    plan = daily.evening_plan(px, idx, {}, [], 100_000, CFG)
    assert plan["new"] == [] and plan["watchlist"][0]["symbol"] == "LEAD"
    assert plan["watchlist"][0]["trigger"] == 119.0


def test_fix_unadjusted_split():
    from v4.importers.india_prices import fix_unadjusted
    px = frame("SPLT", [400.0, 404.0, 101.0, 102.0])
    px.loc[2, "open"] = 101.0
    fixed, fixes = fix_unadjusted(px)
    assert fixes == [("SPLT", str(DAYS[2].date()), -0.75)]
    assert fixed.close.tolist() == pytest.approx([100.0, 101.0, 101.0, 102.0])
    assert fixed.volume.iloc[0] == pytest.approx(3e6 / 0.25)


def test_paper_replay_only_trades_after_start_and_reports_gate():
    from v4.engines.trading import paper
    c, v = leader(after=np.linspace(124, 170, 59))
    idx = pd.Series(np.linspace(100, 200, 320), index=DAYS)
    before = paper.replay(universe(c, v), idx, {}, CFG, start=str(DAYS[270].date()))
    assert before["trades"].empty and before["positions"] == []
    after = paper.replay(universe(c, v), idx, {}, CFG, start=str(DAYS[200].date()))
    assert len(after["trades"]) == 1 and not after["gate"]["met"] and after["gate"]["trades"] == 1
    assert "not live" in paper.gate_line(after["gate"])


def test_paper_open_position_carries_into_evening_plan():
    from v4.engines.trading import paper
    c, v = leader(after=np.linspace(124, 170, 59))
    px = universe(c, v)
    px = px[px.date <= DAYS[266]]                                          # 5 days after entry
    idx = pd.Series(np.linspace(100, 200, 267), index=DAYS[:267])
    r = paper.replay(px, idx, {"LEAD": "Tech"}, CFG, start=str(DAYS[200].date()))
    assert [p.symbol for p in r["positions"]] == ["LEAD"] and r["positions"][0].held == 6


# ---------- B2 rules (D-137) ----------
def test_b2_52_week_breakout_atr_stop_and_trail_exit():
    after = np.r_[np.linspace(124, 160, 30), np.linspace(158, 120, 29)]     # rally, then roll over
    c, v = leader(after=after)
    idx = pd.Series(np.linspace(100, 200, 320), index=DAYS)
    s = sg.signals(sg.indicators(universe(c, v), B2), B2)
    lead = s[s.symbol == "LEAD"]
    assert list(lead.date) == [DAYS[260]]
    atr = 123 * 0.02                                                        # high−low ≈ 2% of price here
    assert lead.stop.iloc[0] == pytest.approx(123 - 2 * atr, rel=0.05)
    t = bt.run(universe(c, v), idx, {"LEAD": "Tech"}, B2)["trades"].iloc[0]
    assert t.exit_reason == "trail: close below 50-day avg" and t.r > 1    # rode the rally, left on the roll-over
    assert t.days > 20                                                       # no 20-day time stop any more


def test_b2_no_new_trades_in_weak_market():
    c, v = leader(after=np.linspace(124, 170, 59))
    weak = pd.Series(np.linspace(200, 100, 320), index=DAYS)              # index below its 200-day average
    assert bt.run(universe(c, v), weak, {}, B2)["trades"].empty
    from v4.engines.trading import daily
    px = universe(c, v)
    plan = daily.evening_plan(px[px.date <= DAYS[260]], weak[:261], {}, [], 100_000, B2)
    assert plan["new"] == [] and ("LEAD", "weak market: no new trades") in plan["skipped"]
    assert "no new trades" in daily.render(plan)
