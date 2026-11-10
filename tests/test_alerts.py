"""Checks the alert sender without contacting Telegram."""
import pytest
import requests
from v4 import alerts


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._p


def test_missing_secrets_fail_loudly(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(alerts.AlertError):
        alerts.send("hi")


def test_sends_to_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    seen = {}

    def fake_post(url, data, timeout):
        seen.update(data)
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(alerts.requests, "post", fake_post)
    alerts.send("hello")
    assert seen["chat_id"] == "123" and seen["text"] == "hello" + alerts.app_link()


def test_error_never_leaks_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "SECRET-TOKEN-XYZ")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")

    def boom(*a, **k):
        raise requests.ConnectionError("https://api.telegram.org/botSECRET-TOKEN-XYZ/sendMessage failed")

    monkeypatch.setattr(alerts.requests, "post", boom)
    with pytest.raises(alerts.AlertError) as e:
        alerts.send("hi")
    assert "SECRET-TOKEN-XYZ" not in str(e.value)


def test_telegram_refusal_is_an_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(alerts.requests, "post",
                        lambda *a, **k: FakeResponse(400, {"ok": False, "description": "chat not found"}))
    with pytest.raises(alerts.AlertError, match="chat not found"):
        alerts.send("hi")


def test_every_message_ends_with_the_app_link(monkeypatch):
    from v4 import alerts
    sent = {}

    class R:
        status_code = 200
        headers = {"content-type": "application/json"}
        def json(self):
            return {"ok": True}

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(alerts.requests, "post", lambda url, data, timeout: sent.update(data) or R())
    alerts.send("hello")
    assert sent["text"].startswith("hello") and sent["text"].endswith("https://pbun4bgte5yek2vgcy7mzn.streamlit.app/")
