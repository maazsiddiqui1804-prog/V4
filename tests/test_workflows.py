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
