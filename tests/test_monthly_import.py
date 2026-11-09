"""Checks the monthly job's file handling without touching NSE or Telegram."""
import datetime as dt
import pytest

from v4.jobs import monthly_import as job
from tests.test_screener_import import NIFTY, SCREENER


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    inbox, archive = tmp_path / "inbox", tmp_path / "archive"
    inbox.mkdir()
    monkeypatch.setattr(job, "INBOX", inbox)
    monkeypatch.setattr(job, "ARCHIVE", archive)
    db = tmp_path / "t.sqlite"
    real = job.import_month
    monkeypatch.setattr(job, "import_month", lambda n, s, d: real(n, s, d, db))
    # Never touch the real database or NAV file from tests.
    from v4.importers import benchmarks as bm
    monkeypatch.setattr(job, "load_benchmark_navs", lambda: bm.load_into_db(tmp_path / "navs.csv", db))
    return inbox, archive


def test_classify(tmp_path):
    (tmp_path / "a.csv").write_text(NIFTY)
    (tmp_path / "b.csv").write_text(SCREENER)
    (tmp_path / "c.csv").write_text("x,y\n1,2\n")
    assert job.classify(tmp_path / "a.csv") == "nse"
    assert job.classify(tmp_path / "b.csv") == "screener"
    assert job.classify(tmp_path / "c.csv") is None


def test_uses_inbox_nse_list_when_nse_down(sandbox, monkeypatch):
    inbox, archive = sandbox
    monkeypatch.setattr(job, "fetch_nse", lambda dest: False)
    (inbox / "export.csv").write_text(SCREENER)
    (inbox / "nse.csv").write_text(NIFTY)
    msg = job.run(dt.date(2026, 12, 1))
    assert "used the one in the inbox" in msg
    assert not list(inbox.glob("*.csv"))                       # inbox emptied
    assert (archive / "2026-12-01" / "screener_export.csv").exists()


def test_reuses_archived_list_and_warns(sandbox, monkeypatch):
    inbox, archive = sandbox
    old = archive / "2026-11-09"
    old.mkdir(parents=True)
    (old / "nifty500_list.csv").write_text(NIFTY)
    monkeypatch.setattr(job, "fetch_nse", lambda dest: False)
    (inbox / "export.csv").write_text(SCREENER)
    msg = job.run(dt.date(2026, 12, 1))
    assert "reused list from 2026-11-09" in msg


def test_no_export_is_an_error(sandbox):
    with pytest.raises(RuntimeError, match="Screener export"):
        job.run(dt.date(2026, 12, 1))


def test_failure_sends_alert(sandbox, monkeypatch):
    sent = []
    monkeypatch.setattr(job.alerts, "send", lambda m: sent.append(m))
    assert job.main() == 1
    assert sent and sent[0].startswith("❌")
