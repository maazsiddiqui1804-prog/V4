"""Checks red-flag matching on items shaped like NSE's real feed."""
import pandas as pd
import pytest

from v4.engines.investment import redflags as rf

WATCH = pd.DataFrame([dict(security_id=1, symbol="EPACKPEB", name="EPack Prefab Technologies Ltd."),
                      dict(security_id=2, symbol="VEDL", name="Vedanta Ltd.")])


def item(title, desc, link="https://x/y.pdf", date="09-Nov-2026 19:19:34"):
    return dict(title=title, description=desc, link=link, pubDate=date)


@pytest.mark.parametrize("desc,expect", [
    ("... regarding Resignation of RAHUL AGARWAL as Chief Financial Officer ... |SUBJECT: Resignation", "CEO/CFO/MD exit"),
    ("... about Resignation of Statutory Auditor |SUBJECT: Change in Directors/KMP/SMP/Auditor/RTA", "auditor exit"),
    ("... Credit Rating downgraded to BBB |SUBJECT: Credit Rating", "credit-rating downgrade"),
    ("... |SUBJECT: Action(s) initiated or orders passed", "regulatory order or penalty"),
    ("... about Resignation of Director/KMP/SMP |SUBJECT: Resignation of Director/KMP/SMP", "director/KMP resignation (check role)"),
    ("... regarding Outcome of Board Meeting |SUBJECT: Outcome of Board Meeting", None),
    ("... about Change in Directors/KMP/SMP/Auditor/RTA |SUBJECT: Change in Directors/KMP/SMP/Auditor/RTA", None),
    ("... Credit Rating reaffirmed AA+ stable |SUBJECT: Credit Rating", None),
])
def test_classify(desc, expect):
    assert rf.classify(desc) == expect


def test_matches_by_name_despite_ltd_vs_limited():
    out = rf.match([item("EPack Prefab Technologies Limited", "Resignation of CFO |SUBJECT: Resignation"),
                    item("Some Other Limited", "Resignation of CFO")], WATCH, "announcements")
    assert [f["symbol"] for f in out] == ["EPACKPEB"]


def test_any_encumbrance_is_a_pledge_flag():
    out = rf.match([item("Vedanta Limited", "NAME OF THE PROMOTER(S) / PACS WHOSE SHARES HAVE BEEN ENCUMBERED : X", "", "")],
                   WATCH, "encumbrance")
    assert out[0]["flag"] == "promoter pledge/encumbrance"


def test_saving_twice_only_alerts_once(tmp_path):
    out = rf.match([item("Vedanta Limited", "Resignation of Chief Executive Officer")], WATCH, "announcements")
    p = tmp_path / "flags.csv"
    assert len(rf.save_new(out, p)) == 1
    assert len(rf.save_new(out, p)) == 0


def test_reviewed_flags_stop_freezing(tmp_path):
    from v4.db import connect, init_db
    db = tmp_path / "t.sqlite"
    init_db(db)
    with connect(db) as c:
        c.execute("INSERT INTO securities (security_id, market, symbol) VALUES (2, 'IN', 'VEDL')")
    p = tmp_path / "flags.csv"
    rf.save_new(rf.match([item("Vedanta Limited", "Resignation of CFO")], WATCH, "announcements"), p)
    rf.load_into_db(p, db)
    with connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM red_flags WHERE reviewed=0").fetchone()[0] == 1
    p.write_text(p.read_text().replace(",\n", ",yes\n").replace(",\r\n", ",yes\r\n"))
    rf.load_into_db(p, db)
    with connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM red_flags WHERE reviewed=0").fetchone()[0] == 0


def test_feed_retries_on_cut_off_file(monkeypatch):
    from v4.importers import filings
    good = b"<rss><channel><item><title>A</title><description>d</description><link>l</link><pubDate>p</pubDate></item></channel></rss>"
    calls = []

    class R:
        def __init__(self, body): self.content = body
        def raise_for_status(self): pass

    def fake_get(*a, **k):
        calls.append(1)
        return R(good[:40] if len(calls) == 1 else good)    # first response cut off

    monkeypatch.setattr(filings.requests, "get", fake_get)
    monkeypatch.setattr("time.sleep", lambda s: None)
    assert filings.fetch("announcements")[0]["title"] == "A" and len(calls) == 2


def test_cut_off_feed_keeps_complete_items():
    from v4.importers import filings
    body = (b"<rss><channel><item><title>A Ltd</title><description>x &amp; y</description><link>l</link><pubDate>p</pubDate></item>"
            b"<item><title>B Ltd</title><description>broken <</description></item><item><title>C")
    items = filings.parse(body)
    assert [i["title"] for i in items] == ["A Ltd", "B Ltd"]
    assert items[0]["description"] == "x & y"


def test_identical_feed_items_flag_once(tmp_path):
    same = item("Vedanta Limited", "NAME OF THE PROMOTER(S) ... ENCUMBERED : X", "", "")
    out = rf.match([same] * 7, WATCH, "encumbrance")
    assert len(rf.save_new(out, tmp_path / "f.csv")) == 1
