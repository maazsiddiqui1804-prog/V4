"""SEC EDGAR (D-096): free official US company data. No key needed.

Plain English:
- company_tickers.json maps tickers to SEC company IDs (CIK).
- submissions/CIK##########.json gives each company's industry code (SIC),
  exchange and filing history.
- companyfacts gives reported financials (used later for quality/growth).
SEC asks automated users to identify themselves and stay under ~10 requests/second.
`probe TICKER,TICKER,...` prints the industry code for each name (no writes).
"""
from __future__ import annotations

import sys
import time

import os

import requests


def headers() -> dict:
    """SEC's fair-access policy requires a contact email in the User-Agent.
    It comes from the SEC_CONTACT_EMAIL GitHub Secret, never from the code."""
    email = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if not email:
        raise RuntimeError("SEC_CONTACT_EMAIL is not set (add it as a GitHub Secret)")
    return {"User-Agent": f"V4 personal research {email}", "Accept-Encoding": "gzip, deflate"}
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def get(url: str, timeout: int = 30) -> dict:
    time.sleep(0.15)   # stay well under SEC's ~10 requests/second
    r = requests.get(url, headers=headers(), timeout=timeout)
    r.raise_for_status()
    return r.json()


def ticker_map() -> dict[str, int]:
    return {v["ticker"].upper(): int(v["cik_str"]) for v in get(TICKERS_URL).values()}


def profile(cik: int) -> dict:
    s = get(SUBMISSIONS_URL.format(cik=cik))
    return {"cik": cik, "name": s.get("name"), "sic": s.get("sic"), "sic_desc": s.get("sicDescription"),
            "exchanges": ",".join(e for e in (s.get("exchanges") or []) if e),
            "state_of_inc": s.get("stateOfIncorporation"), "entity_type": s.get("entityType"),
            "forms": sorted(set((s.get("filings", {}).get("recent", {}) or {}).get("form", [])))}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "probe":
        tmap = ticker_map()
        print(f"SEC ticker map: {len(tmap)} tickers")
        for t in sys.argv[2].split(","):
            cik = tmap.get(t.upper())
            if not cik:
                print(f"{t:6} | not in SEC ticker file")
                continue
            p = profile(cik)
            print(f"{t:6} | SIC {p['sic']} {p['sic_desc']} | {p['exchanges']} | inc {p['state_of_inc']} | {p['name']}")
