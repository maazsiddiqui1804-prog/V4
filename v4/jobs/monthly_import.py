"""Monthly India import job (D-082, D-113, D-118). Runs in GitHub Actions.

Plain English:
1. Maaz drops his Screener export into data/inbox/ on github.com.
2. This job fetches NSE's official Nifty 500 list itself. If NSE can't be reached,
   it uses a list Maaz also dropped in the inbox, or else the last archived one,
   and says so in the report.
3. It imports both, files the raw CSVs under data/archive/<date>/, empties the
   inbox, and sends a Telegram report. Any failure sends a ❌ alert instead.
"""
from __future__ import annotations

import datetime as dt
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from v4 import alerts
from v4.db import ROOT
from v4.importers.screener import import_month
from v4.importers.benchmarks import load_into_db as load_benchmark_navs
from v4.importers.holdings import import_holdings, is_holdings_file

INBOX = ROOT / "data" / "inbox"
ARCHIVE = ROOT / "data" / "archive"
NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
IST = ZoneInfo("Asia/Kolkata")


def classify(path: Path) -> str | None:
    """Tell a Screener export from an NSE list by its column headers."""
    try:
        cols = set(pd.read_csv(path, nrows=0).columns.str.strip())
    except Exception:
        return None
    if {"Symbol", "Series", "ISIN Code"} <= cols:
        return "nse"
    if {"ISIN Code", "Current Price"} <= cols:
        return "screener"
    return None


def fetch_nse(dest: Path) -> bool:
    try:
        r = requests.get(NSE_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 (V4 personal research)"})
        r.raise_for_status()
        dest.write_bytes(r.content)
        return classify(dest) == "nse"
    except requests.RequestException:
        return False


def latest_archived_nse() -> Path | None:
    found = sorted(ARCHIVE.glob("*/nifty500_list.csv"))
    return found[-1] if found else None


def run(today: dt.date | None = None) -> str:
    today = today or dt.datetime.now(IST).date()
    as_of = today.isoformat()
    files = [p for p in INBOX.glob("*.csv")]
    kinds = {p: classify(p) for p in files}
    screener = [p for p, k in kinds.items() if k == "screener"]
    nse_in_inbox = [p for p, k in kinds.items() if k == "nse"]
    unknown = [p.name for p, k in kinds.items() if k is None]
    holdings_files = [p for p in INBOX.glob("*.xlsx") if is_holdings_file(p)]
    unknown += [p.name for p in INBOX.glob("*.xlsx") if p not in holdings_files]

    if len(screener) > 1 or len(holdings_files) > 1:
        raise RuntimeError(f"Expected at most 1 Screener export and 1 holdings file in data/inbox, "
                           f"found {len(screener)} and {len(holdings_files)}")
    if not screener and not holdings_files:
        raise RuntimeError("No Screener export or Console holdings file found in data/inbox")

    lines = []
    if holdings_files:
        # D-119: holdings come from the Console XLSX. The raw file holds the client ID,
        # so it is deleted after import, never archived.
        hrep = import_holdings(holdings_files[0], as_of)
        holdings_files[0].unlink()
        lines.append(hrep.text())
    if not screener:
        status = "⚠️" if any(l.startswith("⚠️") or "⚠️" in l for l in lines) else "✅"
        return "\n".join([f"{status} V4 holdings update — {as_of}"] + lines)

    day_dir = ARCHIVE / as_of
    day_dir.mkdir(parents=True, exist_ok=True)
    nse_path = day_dir / "nifty500_list.csv"
    if fetch_nse(nse_path):
        nse_note = "NSE list: fetched fresh from NSE"
    elif nse_in_inbox:
        shutil.copy(nse_in_inbox[0], nse_path)
        nse_note = "NSE list: NSE unreachable, used the one in the inbox"
    elif (old := latest_archived_nse()) is not None:
        shutil.copy(old, nse_path)
        nse_note = f"⚠️ NSE list: NSE unreachable, reused list from {old.parent.name}"
    else:
        raise RuntimeError("NSE unreachable and no Nifty 500 list in the inbox or archive")

    scr_path = day_dir / "screener_export.csv"
    shutil.move(str(screener[0]), scr_path)
    rep = import_month(nse_path, scr_path, as_of)

    for p in nse_in_inbox:
        p.unlink()
    nav_rows = load_benchmark_navs()

    status = "✅" if not rep.missing_required and not rep.unmatched and "⚠️" not in "".join(lines) else "⚠️"
    lines = [f"{status} V4 monthly India import — {as_of}", rep.text(), nse_note,
             f"Benchmark fund NAVs in database: {nav_rows} rows"] + lines
    if unknown:
        lines.append("Ignored files (not recognised, left in inbox): " + ", ".join(unknown))
    return "\n".join(lines)


def main() -> int:
    try:
        msg = run()
    except Exception as e:  # report every failure; never fail silently
        try:
            alerts.send(f"❌ V4 monthly import FAILED: {e}")
        finally:
            print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print(msg)
    alerts.send(msg[:3900])  # Telegram message limit is 4096 characters
    return 0


if __name__ == "__main__":
    sys.exit(main())
