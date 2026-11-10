"""Kite Connect client: read-only by construction (D-003), login exchange, sealed session."""
import inspect

import pytest

from v4.broker import kite


def test_no_order_capability_anywhere():
    src = inspect.getsource(kite).lower()
    for bad in ["/orders", "place_order", "modify_order", "cancel_order", "/gtt", "requests.put", "requests.delete"]:
        assert bad not in src, f"order capability found: {bad}"


def test_non_read_paths_are_blocked():
    k = kite.Kite("k", "t")
    with pytest.raises(kite.KiteError, match="read-only"):
        k._get("/orders/regular")


def test_checksum_matches_kite_formula():
    import hashlib
    assert kite.checksum("a", "b", "c") == hashlib.sha256(b"abc").hexdigest()


def test_session_sealed_and_only_opens_with_the_secret():
    blob = kite.seal({"access_token": "tok"}, "secret1")
    assert b"tok" not in blob
    assert kite.unseal(blob, "secret1")["access_token"] == "tok"
    with pytest.raises(Exception):
        kite.unseal(blob, "other")


def test_exchange_never_echoes_secrets(monkeypatch):
    class R:
        status_code = 403
    monkeypatch.setattr(kite.requests, "post", lambda *a, **k: R())
    with pytest.raises(kite.KiteError) as e:
        kite.exchange("rt", "key123", "secret456")
    assert "secret456" not in str(e.value) and "key123" not in str(e.value)


def test_instrument_tokens_found():
    from v4.broker import kite_prices as kp
    csv_text = ("instrument_token,tradingsymbol,instrument_type,segment\n"
                "408065,INFY,EQ,NSE\n1,INFY-BE,EQ,NSE\n268041,NIFTY 500,EQ,INDICES\n99,TCS,EQ,NSE\n")
    tok, idx = kp.tokens(csv_text, {"INFY", "WIPRO"})
    assert tok == {"INFY": 408065} and idx == 268041


def test_midday_alerts_once_per_stock_per_day():
    from v4.jobs import kite_ops as ko
    plan = {"actions": [("ABC", "HOLD", "")], "stops": {"ABC": 100.0}, "watchlist": [{"symbol": "XYZ", "trigger": 50.0}]}
    q = {"NSE:ABC": {"last_price": 99.0}, "NSE:XYZ": {"last_price": 51.0}}
    first = ko.midday_alerts(q, plan, set())
    assert {k for k, _ in first} == {"stop:ABC", "trig:XYZ"}
    assert ko.midday_alerts(q, plan, {k for k, _ in first}) == []
    assert ko.midday_alerts({"NSE:ABC": {"last_price": 120.0}}, plan, set()) == []
