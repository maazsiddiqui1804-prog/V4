"""Official NSE filings feeds (D-061, D-109). Red flags only — never a buy signal.

Plain English: NSE publishes free RSS feeds of company filings on its own archive
server. This reads them; the red-flag rules decide which items matter.
`probe` prints a few raw items so the matching rules can be built on the real format.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

import requests

FEEDS = {
    "announcements": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
    "encumbrance": "https://nsearchives.nseindia.com/content/RSS/Sast_ReasonForEncumbrance.xml",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (V4 personal research)", "Accept": "application/rss+xml, text/xml"}


def fetch(feed: str, timeout: int = 30) -> list[dict]:
    r = requests.get(FEEDS[feed], timeout=timeout, headers=HEADERS)
    r.raise_for_status()
    return parse(r.content)


def parse(xml: bytes) -> list[dict]:
    root = ET.fromstring(xml)
    items = []
    for it in root.iter("item"):
        items.append({k: (it.findtext(k) or "").strip() for k in ("title", "link", "description", "pubDate")})
    return items


if __name__ == "__main__":
    if sys.argv[1:] == ["probe"]:
        for name in FEEDS:
            try:
                items = fetch(name)
            except Exception as e:
                print(f"[{name}] FAILED: {type(e).__name__}: {e}")
                continue
            print(f"[{name}] {len(items)} items")
            for it in items[:6]:
                print("  TITLE:", it["title"][:160])
                print("  DESC :", it["description"][:300].replace("\n", " "))
                print("  LINK :", it["link"][:160])
                print("  DATE :", it["pubDate"])
                print("  --")
