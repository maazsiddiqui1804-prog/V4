"""Checks Trading Engine signals, costs and the backtest mechanics on made-up prices."""
import numpy as np
import pandas as pd
import pytest
import yaml

from v4.db import ROOT
from v4.engines.trading import backtest as bt, costs, signals as sg

CFG = yaml.safe_load((ROOT / "config" / "placeholders.yaml").read_text())["trading"]
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
