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
