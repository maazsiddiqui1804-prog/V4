"""Checks the monthly brief's guard and freeze on a tiny sample."""
import pytest
from v4.jobs import monthly_brief as mb


def test_no_brief_before_first_month(tmp_path, monkeypatch):
    from tests.test_screener_import import run as import_sample
    import_sample(tmp_path, as_of="2026-11-09")
    with pytest.raises(mb.SkipBrief, match="2026-12"):
        mb.build(tmp_path / "t.sqlite")
    from v4.db import connect
    with connect(tmp_path / "t.sqlite") as c:
        assert c.execute("SELECT COUNT(*) FROM investment_lists").fetchone()[0] == 0   # nothing frozen
