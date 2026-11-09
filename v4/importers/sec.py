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

import requests

HEADERS = {"User-Agent": "V4 personal research (github.com/maazsiddiqui1804-prog)",
           "Accept-Encoding": "gzip, deflate"}
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def get(url: str, timeout: int = 30) -> dict:
    time.sleep(0.15)   # stay well under SEC's ~10 requests/second
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def ticker_map() -> dict[str, int]:
    return {v["ticker"].upper(): int(v["cik_str"]) for v in get(TICKERS_URL).values()}


def profile(cik: int) -> dict:
    s = get(SUBMISSIONS_URL.format(cik=cik))
    return {"cik": cik, "name": s.get("name"), "sic": s.get("sic"), "sic_desc": s.get("sicDescription"),
            "exchanges": ",".join(e for e in (s.get("exchanges") or []) if e),
            "state_of_inc": s.get("stateOfIncorporation"), "entity_type": s.get("entityType")}


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
