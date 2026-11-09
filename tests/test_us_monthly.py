"""Checks the US pipeline never prices unconfirmed names and keeps stages resumable."""
import json
import pytest
from v4.jobs import us_monthly as job


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "US_DIR", tmp_path / "us")
    monkeypatch.setattr(job, "UNIVERSE", tmp_path / "us_universe.csv")
    job.write_csv(tmp_path / "us" / "shortlist.csv", [
        {"ticker": "YES1", "zerodha_checked": "yes"}, {"ticker": "NOPE", "zerodha_checked": "no"},
        {"ticker": "UNCHK", "zerodha_checked": ""}, {"ticker": "YES2", "zerodha_checked": "yes"}])
    calls = []
    monkeypatch.setattr(job, "tiingo_history", lambda t, s: calls.append(t) or [("d", 1.0)] * 260)
    return tmp_path, calls


def test_prices_only_for_kite_confirmed(sandbox):
    tmp, calls = sandbox
    msg = job.stage_prices()
    assert calls == ["YES1", "YES2"] and "2 not Kite-confirmed" in msg


def test_prices_resume_and_respect_budget(sandbox):
    tmp, calls = sandbox
    job.stage_prices(budget=1)
    assert calls == ["YES1"]
    job.stage_prices(budget=1)
    assert calls == ["YES1", "YES2"]                       # second run picks up where the first stopped
    job.stage_prices(budget=5)
    assert calls == ["YES1", "YES2"]                       # nothing refetched within the month
    data = json.loads((tmp / "us" / "prices.json").read_text())
    assert set(data) == {"YES1", "YES2"}


def test_job_minutes_round_up_like_github():
    from v4.jobs.actions_minutes import job_minutes
    assert job_minutes("2026-11-09T10:00:00Z", "2026-11-09T10:00:05Z") == 1
    assert job_minutes("2026-11-09T10:00:00Z", "2026-11-09T10:02:01Z") == 3
    assert job_minutes(None, None) == 0


def test_size_check_drops_small_foreign_filers_only(sandbox):
    import pandas as pd
    tmp, _ = sandbox
    job.write_csv(job.UNIVERSE, [
        {"ticker": "BIGF", "cik": 1, "size_basis": "to confirm after Kite check (foreign filer)"},
        {"ticker": "SMLF", "cik": 2, "size_basis": "to confirm after Kite check (foreign filer)"},
        {"ticker": "USCO", "cik": 3, "size_basis": "public float"}])
    short = pd.DataFrame({"ticker": ["BIGF", "SMLF", "USCO"]})
    prices = {"BIGF": {"price": 100.0}, "SMLF": {"price": 50.0}, "USCO": {"price": 1.0}}
    shares = {1: 1e9, 2: 3e7, 3: 10}
    kept, dropped = job.size_check(short, prices, 10e9, shares.get)
    assert kept.ticker.tolist() == ["BIGF", "USCO"] and dropped == ["SMLF (~$1.5B)"]


def test_eps_converted_only_with_confirmed_adr_ratio():
    import math
    import pandas as pd
    short = pd.DataFrame({"ticker": ["TSM", "SAP", "MSFT"], "currency": ["TWD", "EUR", "USD"], "eps": [45.0, 6.0, 18.0]})
    eps = job.eps_in_listing_terms(short, {"TWD": 1 / 32, "EUR": 1.1}, {"TSM": 5})
    assert eps.iloc[0] == 45.0 / 32 * 5 and math.isnan(eps.iloc[1]) and eps.iloc[2] == 18.0
