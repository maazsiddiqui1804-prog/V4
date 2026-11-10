"""Daily app refresh: merging new days, snapshot facts."""
import numpy as np
import pandas as pd
import pytest
from v4.importers import india_prices as ip
from v4.jobs import daily_app as da


def test_merge_replaces_redownloaded_days():
    old = pd.DataFrame({"date": pd.to_datetime(["2026-11-05", "2026-11-06"]), "symbol": "A", "open": 1, "high": 1,
                        "low": 1, "close": [100.0, 101.0], "volume": 1})
    new = pd.DataFrame({"date": pd.to_datetime(["2026-11-06", "2026-11-09"]), "symbol": "A", "open": 1, "high": 1,
                        "low": 1, "close": [101.5, 103.0], "volume": 1})
    m = ip.merge(old, new)
    assert m.close.tolist() == [100.0, 101.5, 103.0]


def test_snapshot_facts():
    d = pd.bdate_range("2025-01-01", periods=300)
    px = pd.DataFrame({"date": d, "symbol": "A", "close": np.linspace(100, 199, 300)})
    s = da.snapshot(px, {}).iloc[0]
    assert s.close == pytest.approx(199) and s.high_52w == pytest.approx(199)
    assert s.chg_1y == pytest.approx(199 / px.close.iloc[-253] - 1)
    assert s.dma50 == pytest.approx(px.close.iloc[-50:].mean())


def test_missed_login_streak_counts_weekdays_only():
    import datetime as dt
    today = dt.date(2026, 12, 14)                      # Monday
    assert da.missed_streak(["2026-12-11"], today) == 0     # logged in Friday
    assert da.missed_streak(["2026-12-09"], today) == 2     # missed Thu + Fri (weekend not counted)
    assert da.missed_streak([], today) >= 3


def test_kite_off_by_default():
    assert da.kite_today() == (None, "off")
