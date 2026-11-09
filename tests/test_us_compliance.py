"""Checks the D-132 US safeguards."""
import datetime as dt
from v4.engines.us import compliance as c

R = {"tcs_threshold_inr": 1_000_000, "tcs_warn_fraction": 0.8, "estate_warn_usd": 45_000, "w8ben_remind_days": 60}


def test_financial_year_boundary():
    assert c.fy_of(dt.date(2027, 3, 31)) == "FY2026-27"
    assert c.fy_of(dt.date(2027, 4, 1)) == "FY2027-28"


def test_remittance_warnings_only_count_this_fy():
    rows = [{"date": "2026-03-15", "inr": 900_000}, {"date": "2026-05-01", "inr": 500_000}]
    today = dt.date(2026, 11, 10)
    assert c.remittance_warnings(rows, today, R) == []
    rows.append({"date": "2026-10-01", "inr": 350_000})
    assert "nearing" in c.remittance_warnings(rows, today, R)[0]
    rows.append({"date": "2026-11-01", "inr": 200_000})
    assert "above" in c.remittance_warnings(rows, today, R)[0]


def test_schedule_fa_calendar_year():
    rows = [{"date": "2026-12-20", "ticker": "NVDA", "usd_value": 100},
            {"date": "2027-01-05", "ticker": "NVDA", "usd_value": 110},
            {"date": "2027-06-30", "ticker": "NVDA", "usd_value": 150},
            {"date": "2027-12-31", "ticker": "NVDA", "usd_value": 130}]
    fa = c.schedule_fa(rows, 2027)
    assert fa == [{"ticker": "NVDA", "year": 2027, "initial_usd": 110, "peak_usd": 150, "closing_usd": 130}]


def test_estate_uses_latest_snapshot():
    rows = [{"date": "2027-01-01", "ticker": "A", "usd_value": 50_000},
            {"date": "2027-02-01", "ticker": "A", "usd_value": 30_000},
            {"date": "2027-02-01", "ticker": "B", "usd_value": 10_000}]
    assert c.estate_warning(rows, R) == []
    rows.append({"date": "2027-02-01", "ticker": "C", "usd_value": 6_000})
    assert c.estate_warning(rows, R)


def test_w8ben():
    assert "not recorded" in c.w8ben_reminder(None, dt.date(2026, 12, 1), R)[0]
    assert c.w8ben_reminder("2026-12-01", dt.date(2029, 10, 1), R) == []
    assert "expires 31 Dec 2029" in c.w8ben_reminder("2026-12-01", dt.date(2029, 11, 15), R)[0]
