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


def _row(end, val, filed="2026-02-01", form="10-K", start=None):
    r = {"end": end, "val": val, "filed": filed, "form": form}
    if start:
        r["start"] = start
    return r


def test_label_switch_is_merged():
    from v4.engines.us import fundamentals as fu
    facts = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [_row("2010-06-30", 60, start="2009-07-01")]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            _row("2025-06-30", 280, start="2024-07-01"), _row("2026-06-30", 320, start="2025-07-01")]}}}}}
    assert list(fu.annual_series(facts, "revenue", "USD")) == ["2010-06-30", "2025-06-30", "2026-06-30"]


def test_convenience_usd_not_mixed_with_home_currency():
    from v4.engines.us import fundamentals as fu
    rows_twd = [_row(f"{y}-12-31", 2e12, form="20-F", start=f"{y}-01-01") for y in (2021, 2022, 2023, 2024)]
    facts = {"facts": {"ifrs-full": {"Revenue": {"units": {
        "TWD": rows_twd, "USD": [_row("2024-12-31", 8.8e10, filed="2026-04-01", form="20-F", start="2024-01-01")]}}}}}
    cur = fu.reporting_currency(facts)
    assert cur == "TWD" and fu.annual_series(facts, "revenue", cur)["2024-12-31"] == 2e12
