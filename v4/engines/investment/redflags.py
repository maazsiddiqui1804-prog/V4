"""Red-flag filings (D-061, D-109, D-127). A risk alarm only — never a buy signal.

Plain English:
- Watches V4's holdings plus the current month's top 20 (the names it might buy).
- Reads NSE's official filings feeds ~3× a day and matches items to watched
  companies by name.
- Flags (D-061): auditor exit · CEO/CFO/MD exit (and any director/KMP resignation,
  marked "check role") · credit-rating downgrade · regulatory order or penalty ·
  promoter pledge/encumbrance.
- New flags go to Telegram and into data/red_flags.csv (a small text file, so the
  repo doesn't bloat). A flagged stock is not bought until the flag is marked reviewed;
  a held stock shows REVIEW in the monthly brief (no automatic sell, D-127).
- To mark one reviewed: tell Claude, or set its 'reviewed' column to 'yes' on GitHub.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

from v4.db import ROOT, connect, init_db, DB_PATH

FLAGS_CSV = ROOT / "data" / "red_flags.csv"
FIELDS = ["key", "detected", "symbol", "company", "flag", "subject", "link", "reviewed"]
GENERIC = "change in directors/kmp/smp/auditor/rta"


def norm(name: str) -> str:
    n = name.lower().replace("&", " and ")
    n = re.sub(r"\b(limited|ltd|the|india|co|company|corporation|corp)\b\.?", " ", n)
    return re.sub(r"[^a-z0-9]+", "", n)


def classify(text: str) -> str | None:
    """Return the red-flag type for one announcement, or None."""
    t = text.lower().replace(GENERIC, " ")
    leaving = re.search(r"resign|cessation|removal|vacat|step(ped|s)? down", t)
    if leaving and "auditor" in t:
        return "auditor exit"
    if leaving and re.search(r"chief executive|\bceo\b|chief financial|\bcfo\b|managing director|\bmd\b", t):
        return "CEO/CFO/MD exit"
    if re.search(r"credit rating|rating", t) and re.search(r"downgrad|negative|default|\bd\b rating", t):
        return "credit-rating downgrade"
    if re.search(r"action\(s\) initiated or orders passed|show cause|penalt|order passed|adjudicat|search and seizure|search & seizure", t):
        return "regulatory order or penalty"
    if leaving and re.search(r"director|kmp", t):
        return "director/KMP resignation (check role)"
    return None


def watchlist(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Holdings + latest month's top 20, with names for matching."""
    with connect(db_path) as c:
        month = c.execute("SELECT MAX(list_month) FROM investment_lists").fetchone()[0]
        rows = c.execute(
            """SELECT DISTINCT s.security_id, s.symbol, s.name FROM securities s
               WHERE s.security_id IN (
                   SELECT security_id FROM holdings_snapshots
                    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM holdings_snapshots))
                  OR s.security_id IN (
                   SELECT security_id FROM investment_lists WHERE list_month = ? AND rank <= 20)""",
            (month,)).fetchall()
    return pd.DataFrame(rows, columns=["security_id", "symbol", "name"])


def match(items: list[dict], watch: pd.DataFrame, feed: str) -> list[dict]:
    by_name = {norm(n): (sid, sym, n) for sid, sym, n in watch[["security_id", "symbol", "name"]].itertuples(index=False) if n}
    out = []
    for it in items:
        hit = by_name.get(norm(it["title"]))
        if not hit:
            continue
        text = f"{it['title']} {it['description']}"
        flag = "promoter pledge/encumbrance" if feed == "encumbrance" else classify(text)
        if not flag:
            continue
        subject = it["description"].split("SUBJECT:")[-1].strip()[:120] if feed != "encumbrance" else it["description"][:120]
        key = hashlib.sha1(f"{feed}|{it['title']}|{it['description']}|{it['link']}|{it['pubDate']}".encode()).hexdigest()[:16]
        out.append({"key": key, "detected": it["pubDate"], "symbol": hit[1], "company": hit[2],
                    "flag": flag, "subject": subject, "link": it["link"], "reviewed": ""})
    return out


def save_new(flags: list[dict], path: Path = FLAGS_CSV) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        with path.open() as f:
            seen = {r["key"] for r in csv.DictReader(f)}
    new = []
    for f in flags:                     # the feed repeats identical items: keep one of each
        if f["key"] not in seen:
            seen.add(f["key"])
            new.append(f)
    write_header = not path.exists()
    with path.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(new)
    return new


def load_into_db(path: Path = FLAGS_CSV, db_path: Path = DB_PATH) -> int:
    """Copy open (unreviewed) flags into the database for the monthly brief."""
    init_db(db_path)
    if not path.exists():
        return 0
    with path.open() as f, connect(db_path) as c:
        rows = list(csv.DictReader(f))
        ids = dict(c.execute("SELECT symbol, security_id FROM securities WHERE market='IN'").fetchall())
        c.execute("DELETE FROM red_flags")
        c.executemany("INSERT INTO red_flags (detected_at, security_id, flag_type, source_url, reviewed) VALUES (?,?,?,?,?)",
                      [(r["detected"], ids[r["symbol"]], r["flag"], r["link"],
                        1 if r["reviewed"].strip().lower() in ("yes", "y", "1", "true") else 0)
                       for r in rows if r["symbol"] in ids])
    return len(rows)


def dry_run(symbols: list[str]) -> int:
    """Match live feeds against named stocks; print only — nothing saved, nothing sent."""
    from v4.importers import filings
    with connect(DB_PATH) as c:
        rows = c.execute(f"SELECT security_id, symbol, name FROM securities WHERE symbol IN ({','.join('?' * len(symbols))})",
                         symbols).fetchall()
    watch = pd.DataFrame(rows, columns=["security_id", "symbol", "name"])
    print(f"Dry run on {len(watch)} names: {', '.join(watch.symbol)}")
    for feed in filings.FEEDS:
        items = filings.fetch(feed)
        hits = match(items, watch, feed)
        print(f"[{feed}] {len(items)} items, {len(hits)} red flags")
        for f in hits[:10]:
            print(f"  {f['symbol']} — {f['flag']}: {f['subject']}")
    return 0


def main() -> int:
    from v4 import alerts
    from v4.importers import filings
    if len(sys.argv) > 2 and sys.argv[1] == "dryrun":
        return dry_run(sys.argv[2].split(","))
    try:
        watch = watchlist()
        if watch.empty:
            print("Watchlist empty (no holdings, no monthly list yet) — nothing to check")
            return 0
        found = []
        for feed in filings.FEEDS:
            found += match(filings.fetch(feed), watch, feed)
        new = save_new(found)
        print(f"Checked {len(watch)} watched names: {len(new)} new red flags")
        if new:
            lines = ["🚩 V4 red flag" + ("s" if len(new) > 1 else "") + " (official NSE filings):"]
            for f in new:
                lines.append(f"• {f['symbol']} — {f['flag']}: {f['subject']}\n  {f['link'] or '(no link)'}")
            lines.append("Buying these is frozen until reviewed (D-061). Tell Claude when you've read them.")
            alerts.send("\n".join(lines)[:3900])
        return 0
    except Exception as e:
        alerts.send(f"❌ V4 red-flag check FAILED: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
