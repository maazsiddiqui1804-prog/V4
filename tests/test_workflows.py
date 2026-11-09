"""Every cloud workflow file must be valid, and every one must alert Telegram on failure."""
from pathlib import Path
import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parent.parent / ".github" / "workflows").glob("*.yml"))


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_parses(wf):
    data = yaml.safe_load(wf.read_text())
    assert "jobs" in data


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_alerts_on_failure(wf):
    # CLAUDE.md: silence must never mean "broken".
    text = wf.read_text()
    assert "if: failure()" in text and "v4.alerts" in text


def test_every_scheduled_job_is_watched_for_silence():
    """A scheduled workflow must be in the Monday staleness check (except the checker itself)."""
    import yaml
    from pathlib import Path
    from v4.jobs.actions_minutes import EXPECTED
    wf_dir = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    scheduled = {p.name for p in wf_dir.glob("*.yml")
                 if "schedule" in (yaml.safe_load(p.read_text()).get(True) or yaml.safe_load(p.read_text()).get("on") or {})}
    assert scheduled - {"health_check.yml"} == set(EXPECTED)


def test_stale_job_detection(monkeypatch):
    import datetime as dt
    from v4.jobs import actions_minutes as am
    now = dt.datetime(2026, 11, 16, 3, 17, tzinfo=dt.timezone.utc)
    runs = {"benchmark_navs.yml": "2026-11-13T17:20:00Z", "red_flags.yml": "2026-11-05T09:55:00Z"}
    monkeypatch.setattr(am, "_get", lambda url, params=None: {"workflow_runs": [
        {"updated_at": runs[url.split("/workflows/")[1].split("/")[0]]}]})
    out = am.stale_jobs("o/r", now)
    assert len(out) == 1 and out[0].startswith("red_flags.yml")
