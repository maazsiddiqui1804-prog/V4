"""Dashboard loads both views on the repo's real data without errors."""
import pytest

st = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


def test_both_views_render():
    at = AppTest.from_file("../dashboard/app.py", default_timeout=60).run()
    assert not at.exception
    assert any("Action" in h.value for h in at.header)
    at.radio[0].set_value("Analysis").run()
    assert not at.exception
    assert any("SIMULATION" in s.value for s in at.subheader)
