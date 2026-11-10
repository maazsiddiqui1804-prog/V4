"""Telegram alerts (D-004). Every V4 job reports through here.

Plain English: send(text) posts a message to Maaz's V4 Alerts bot.
The bot token and chat ID come from GitHub Secrets via environment
variables. They are never written to files or printed.
"""
import os
import sys

import requests

API = "https://api.telegram.org/bot{token}/sendMessage"


class AlertError(RuntimeError):
    pass


def app_link() -> str:
    """'📱 Open app: <url>' from config/app.yaml, or '' if it's missing."""
    try:
        import yaml
        from pathlib import Path
        url = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "app.yaml").read_text())["url"]
        return f"\n\n📱 Open app: {url}"
    except Exception:
        return ""


def send(text: str, timeout: int = 20) -> None:
    text = text + app_link()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise AlertError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set")
    try:
        r = requests.post(API.format(token=token),
                          data={"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}, timeout=timeout)
    except requests.RequestException as e:
        # Never echo the URL: it contains the token.
        raise AlertError(f"Could not reach Telegram ({type(e).__name__})") from None
    if r.status_code != 200 or not r.json().get("ok"):
        desc = r.json().get("description", "") if r.headers.get("content-type", "").startswith("application/json") else ""
        raise AlertError(f"Telegram refused the message: HTTP {r.status_code} {desc}")


if __name__ == "__main__":
    send(" ".join(sys.argv[1:]) or "V4 test message")
    print("Alert sent.")
