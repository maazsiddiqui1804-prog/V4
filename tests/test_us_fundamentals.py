"""Checks annual-figure extraction on a hand-made SEC-shaped payload."""
from v4.engines.us import fundamentals as fu

FACTS = {"facts": {"us-gaap": {
    "Revenues": {"units": {"USD": [
        {"start": "2024-01-01", "end": "2024-12-31", "val": 100, "form": "10-K", "filed": "2025-02-01"},
        {"start": "2024-10-01", "end": "2024-12-31", "val": 30, "form": "10-K", "filed": "2025-02-01"},   # quarter inside 10-K
        {"start": "2025-01-01", "end": "2025-12-31", "val": 120, "form": "10-K", "filed": "2026-02-01"},
        {"start": "2025-01-01", "end": "2025-12-31", "val": 121, "form": "10-K/A", "filed": "2026-05-01"},  # amendment wins
        {"start": "2025-04-01", "end": "2025-06-30", "val": 31, "form": "10-Q", "filed": "2025-08-01"},
    ]}},
    "Assets": {"units": {"USD": [{"end": "2025-12-31", "val": 500, "form": "10-K", "filed": "2026-02-01"}]}},
    "EarningsPerShareDiluted": {"units": {"USD/shares": [
        {"start": "2025-01-01", "end": "2025-12-31", "val": 2.5, "form": "10-K", "filed": "2026-02-01"}]}},
}, "ifrs-full": {}}}


def test_annual_only_full_year_latest_filing_wins():
    assert fu.annual_series(FACTS, "revenue") == {"2024-12-31": 100.0, "2025-12-31": 121.0}


def test_balance_sheet_items_have_no_period():
    assert fu.annual_series(FACTS, "assets") == {"2025-12-31": 500.0}


def test_eps_unit_is_per_share():
    assert fu.annual_series(FACTS, "eps_diluted") == {"2025-12-31": 2.5}


def test_missing_item_is_empty():
    assert fu.annual_series(FACTS, "cfo") == {}
