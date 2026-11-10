"""Telegram digests carry every action item."""
import datetime as dt
from v4.jobs import digest


def test_weekly_lists_waiting_items_and_dates():
    msg = digest.weekly(dt.date(2026, 11, 16))
    assert "DO NOW" in msg and "WAITING ON YOU" in msg and "COMING UP" in msg
    assert "W-8BEN" in msg and "1 Dec" in msg


def test_monthly_reminder_only_from_first_brief_month():
    assert digest.monthly(dt.date(2026, 11, 1)) is None
    m = digest.monthly(dt.date(2026, 12, 1))
    assert m and "data/inbox" in m


def test_kite_line_only_when_on():
    assert digest.kite_line({"kite_enabled": False}) is None
    assert "/kite" in digest.kite_line({"kite_enabled": True, "url": "https://x.app/"})
