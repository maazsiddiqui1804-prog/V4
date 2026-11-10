"""Kite Connect — READ-ONLY client and daily session handling (D-080, D-081, D-106). Switched off until
Maaz subscribes after the GMAT (config/app.yaml → kite_enabled).

HARD LIMIT (D-003): this module can only READ (profile, holdings, positions, quotes, historical candles,
instrument list). It has no way to place, modify or cancel an order — and a test fails if one is added.

Daily login (D-081) — one tap, never a stored password or 2FA secret:
1. Maaz taps "Log in to Kite" in the app (or the Telegram reminder link) → Kite's own login page.
2. Kite sends him back to the app's Kite page with a one-time request_token.
3. The app passes only that token to a GitHub job (repository_dispatch "kite-login").
4. The job swaps it for the day's access token using the API secret held in GitHub Secrets, encrypts it
   with a key derived from that secret, and stores it as a 1-day private artifact. The token is never
   written to the repo, a log, or Telegram. It expires at 6 AM next day by regulation.
5. Later jobs that day load and decrypt it. No login today → trading runs are skipped and Telegram says so.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import zipfile

import requests

API = "https://api.kite.trade"
LOGIN = "https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"
HEAD = {"X-Kite-Version": "3"}
ARTIFACT = "kite-session"
READ_ONLY_PATHS = ("/user/profile", "/portfolio/holdings", "/portfolio/positions", "/quote",
                   "/quote/ohlc", "/quote/ltp", "/instruments", "/instruments/historical/")


class KiteError(Exception):
    pass


def checksum(api_key: str, request_token: str, api_secret: str) -> str:
    return hashlib.sha256((api_key + request_token + api_secret).encode()).hexdigest()


def _fernet(api_secret: str):
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256(("v4-kite-session:" + api_secret).encode()).digest())
    return Fernet(key)


def exchange(request_token: str, api_key: str, api_secret: str) -> dict:
    """request_token → {'access_token', 'user_id', 'login_time'} (raises on failure; never echoes secrets)."""
    r = requests.post(f"{API}/session/token", headers=HEAD, timeout=20,
                      data={"api_key": api_key, "request_token": request_token,
                            "checksum": checksum(api_key, request_token, api_secret)})
    if r.status_code != 200:
        raise KiteError(f"Kite login exchange refused (HTTP {r.status_code})")
    d = r.json().get("data", {})
    return {"access_token": d["access_token"], "user_id": d.get("user_id"), "login_time": d.get("login_time")}


def seal(session: dict, api_secret: str) -> bytes:
    return _fernet(api_secret).encrypt(json.dumps(session).encode())


def unseal(blob: bytes, api_secret: str) -> dict:
    return json.loads(_fernet(api_secret).decrypt(blob))


def load_session(repo: str, gh_token: str, api_secret: str) -> dict | None:
    """Today's session from the latest unexpired 'kite-session' artifact, or None if Maaz hasn't logged in."""
    h = {"Authorization": f"Bearer {gh_token}", "Accept": "application/vnd.github+json"}
    arts = requests.get(f"https://api.github.com/repos/{repo}/actions/artifacts", headers=h,
                        params={"name": ARTIFACT, "per_page": 5}, timeout=20).json().get("artifacts", [])
    arts = [a for a in arts if not a.get("expired")]
    if not arts:
        return None
    z = requests.get(arts[0]["archive_download_url"], headers=h, timeout=30)
    if z.status_code != 200:
        return None
    with zipfile.ZipFile(io.BytesIO(z.content)) as f:
        return unseal(f.read("session.bin"), api_secret)


class Kite:
    """Read-only Kite Connect client."""

    def __init__(self, api_key: str, access_token: str):
        self._h = dict(HEAD, Authorization=f"token {api_key}:{access_token}")

    def _get(self, path: str, params=None):
        if not path.startswith(READ_ONLY_PATHS):
            raise KiteError(f"blocked: {path} is not a read-only endpoint (D-003)")
        r = requests.get(API + path, headers=self._h, params=params, timeout=30)
        if r.status_code == 403:
            raise KiteError("Kite session expired or not logged in today")
        r.raise_for_status()
        return r.json()["data"] if "json" in r.headers.get("content-type", "") else r.text

    def profile(self):
        return self._get("/user/profile")

    def holdings(self):
        return self._get("/portfolio/holdings")

    def positions(self):
        return self._get("/portfolio/positions")

    def ohlc(self, instruments: list[str]):
        """instruments like 'NSE:INFY' (≤1000 per call)."""
        return self._get("/quote/ohlc", params=[("i", x) for x in instruments])

    def instruments(self, exchange: str = "NSE") -> str:
        return self._get(f"/instruments/{exchange}")

    def historical(self, instrument_token: int, start: str, end: str, interval: str = "day"):
        return self._get(f"/instruments/historical/{instrument_token}/{interval}",
                         params={"from": start, "to": end})


def from_env() -> Kite | None:
    """Client for scheduled jobs, or None when not logged in today (caller skips and alerts)."""
    key, secret = os.environ.get("KITE_API_KEY"), os.environ.get("KITE_API_SECRET")
    repo, gh = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not all([key, secret, repo, gh]):
        return None
    s = load_session(repo, gh, secret)
    return Kite(key, s["access_token"]) if s else None


def main_exchange() -> int:
    """Used by the kite-login job: exchange the request token and write the sealed session file."""
    import sys
    from v4 import alerts
    try:
        s = exchange(os.environ["REQUEST_TOKEN"], os.environ["KITE_API_KEY"], os.environ["KITE_API_SECRET"])
        os.makedirs("kite_session", exist_ok=True)
        with open("kite_session/session.bin", "wb") as f:
            f.write(seal(s, os.environ["KITE_API_SECRET"]))
        alerts.send("🔑 Kite connected for today (valid until 6 AM tomorrow).")
        print("Kite session stored")
        return 0
    except Exception as e:
        alerts.send(f"❌ Kite login failed: {e}. Tap Log in to Kite in the app to try again.")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main_exchange())
