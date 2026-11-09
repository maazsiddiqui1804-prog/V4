"""Checks the shadow-portfolio comparison behind the 12-month warning and 3-year kill test."""
import pytest
from v4.engines import review as rv

LINE = {"2027-01-01": 100.0, "2027-02-01": 110.0, "2028-01-03": 121.0, "2030-01-02": 150.0}


def test_shadow_buys_each_contribution_at_that_days_level():
    c = [("2027-01-01", 1000), ("2027-02-01", 1100)]
    assert rv.shadow_value(c, LINE, "2028-01-03") == pytest.approx(1000 * 1.21 + 1100 * 121 / 110)


def test_contribution_on_holiday_uses_next_available_day():
    assert rv.shadow_value([("2027-01-15", 1000)], LINE, "2027-02-01") == pytest.approx(1000)


def test_12_month_warning_only_when_lagging_both():
    c = [("2027-01-01", 1000)]
    lines = {"nifty500": LINE, "quality30": {"2027-01-01": 100.0, "2028-01-03": 105.0}}
    v = rv.verdict("2027-01-01", "2028-01-03", 1100, 0, c, lines)     # beats quality (1050), lags nifty (1210)
    assert v["stage"].startswith("12-month") and v["action"].startswith("OK")
    v = rv.verdict("2027-01-01", "2028-01-03", 1000, 0, c, lines)
    assert "deep review" in v["action"]


def test_kill_test_needs_to_beat_both():
    c = [("2027-01-01", 1000)]
    lines = {"nifty500": LINE, "quality30": {"2027-01-01": 100.0, "2030-01-02": 140.0}}
    v = rv.verdict("2027-01-01", "2030-01-02", 1450, 0, c, lines)
    assert v["stage"].startswith("kill") and v["action"].startswith("FAIL") and "nifty500" in v["action"]
    assert rv.verdict("2027-01-01", "2030-01-02", 1600, 0, c, lines)["action"].startswith("PASS")
