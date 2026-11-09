"""Benchmark fund prices (D-121): index-fund NAVs from AMFI's official daily file.

Plain English:
- AMFI publishes every mutual fund's latest NAV each day in one text file.
- V4 tracks the index funds named in config/benchmarks.yaml (Direct, Growth).
- `record` appends today's NAVs to data/benchmarks/navs.csv (a small text file,
  so the repo doesn't bloat the way a daily database commit would).
- `discover` lists every Direct-Growth fund whose name matches each benchmark,
  so Maaz can approve which funds to track.
- `load` copies navs.csv into the database (run by the monthly job).
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
import yaml

from v4.db import ROOT, connect, init_db, DB_PATH

AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
CONFIG = ROOT / "config" / "benchmarks.yaml"
NAV_CSV = ROOT / "data" / "benchmarks" / "navs.csv"
FIELDS = ["date", "scheme_code", "benchmark", "nav", "scheme_name"]


def fetch_amfi(timeout: int = 60) -> str:
    r = requests.get(AMFI_URL, timeout=timeout, headers={"User-Agent": "V4 personal research"})
    r.raise_for_status()
    return r.text


def parse_amfi(text: str) -> list[dict]:
    """Rows are 'code;isin;isin;name;...;nav;date'. Section headings and blanks are skipped."""
    out = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        try:
            nav = float(parts[-2])
            date = datetime.strptime(parts[-1], "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        # Newer files have separate Plan and Option columns before NAV and Date.
        extra = " ".join(parts[4:-2])
        out.append({"scheme_code": parts[0], "scheme_name": parts[3], "plan_option": extra,
                    "nav": nav, "date": date})
    return out


def is_direct_growth(row: dict) -> bool:
    n = (row["scheme_name"] + " " + row.get("plan_option", "")).lower()
    return "direct" in n and "growth" in n and not re.search(r"idcw|dividend|\betf\b", n)


def load_config() -> dict:
    return yaml.safe_load(CONFIG.read_text())["benchmarks"]


def discover(rows: list[dict], cfg: dict) -> dict[str, list[dict]]:
    found = {}
    for key, b in cfg.items():
        pat = re.compile(b["match"], re.I)
        excl = re.compile(b["exclude"], re.I) if b.get("exclude") else None
        found[key] = [r for r in rows if pat.search(r["scheme_name"])
                      and is_direct_growth(r)
                      and not (excl and excl.search(r["scheme_name"]))]
    return found


def record(rows: list[dict], cfg: dict, path: Path = NAV_CSV, strict: bool = True) -> int:
    wanted = {str(code): key for key, b in cfg.items() for code in (b.get("scheme_codes") or [])}
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        with path.open() as f:
            seen = {(r["date"], r["scheme_code"]) for r in csv.DictReader(f)}
    new = [r for r in rows if r["scheme_code"] in wanted and (r["date"], r["scheme_code"]) not in seen]
    write_header = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        for r in sorted(new, key=lambda r: (r["date"], r["scheme_code"])):
            w.writerow({"date": r["date"], "scheme_code": r["scheme_code"],
                        "benchmark": wanted[r["scheme_code"]], "nav": r["nav"],
                        "scheme_name": r["scheme_name"]})
    missing = set(wanted) - {r["scheme_code"] for r in rows}
    if missing and strict:
        raise RuntimeError(f"Benchmark funds missing from AMFI file: {sorted(missing)}")
    return len(new)


HISTORY_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"


def _col(idx: dict, *names: str) -> int:
    """Find a column by name, ignoring case and extra spaces."""
    norm = {re.sub(r"\s+", " ", k).strip().lower(): v for k, v in idx.items()}
    for n in names:                       # exact name first...
        if n in norm:
            return norm[n]
    for n in names:                       # ...then a looser match
        for k, v in norm.items():
            if n in k:
                return v
    raise KeyError(f"none of {names} in header {list(idx)}")


def parse_amfi_history(text: str) -> list[dict]:
    """AMFI's history report puts columns in a different order; read them by header name."""
    out, cols = [], None
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(";")]
        low = line.lower()
        if "scheme code" in low and "net asset value" in low and "date" in low:
            idx = {name: i for i, name in enumerate(parts)}
            cols = {"code": _col(idx, "scheme code"), "name": _col(idx, "scheme name", "nav name", "fund name", "scheme"),
                    "nav": _col(idx, "net asset value"), "date": _col(idx, "date")}
            continue
        if cols is None or len(parts) <= max(cols.values()) or not parts[cols["code"]].isdigit():
            continue
        try:
            nav = float(parts[cols["nav"]])
            date = datetime.strptime(parts[cols["date"]], "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        out.append({"scheme_code": parts[cols["code"]], "scheme_name": parts[cols["name"]],
                    "nav": nav, "date": date})
    return out


def backfill(days: int = 420, chunk: int = 90) -> int:
    """One-off: fetch past NAVs for the tracked funds, 90 days per request (AMFI's limit)."""
    from datetime import date as d, timedelta
    import time
    cfg = load_config()
    end = d.today()
    start = end - timedelta(days=days)
    total = 0
    while start < end:
        stop = min(start + timedelta(days=chunk - 1), end)
        r = requests.get(HISTORY_URL, timeout=180, headers={"User-Agent": "V4 personal research"},
                         params={"tp": "1", "frmdt": start.strftime("%d-%b-%Y"), "todt": stop.strftime("%d-%b-%Y")})
        r.raise_for_status()
        if total == 0 and start == end - timedelta(days=days):
            head = next((l for l in r.text.splitlines() if "scheme" in l.lower()), "(no header line found)")
            print(f"History file header: {head[:200]}")
        rows = parse_amfi_history(r.text)
        n = record(rows, cfg, strict=False)
        print(f"{start} → {stop}: {len(r.content)/1e6:.1f} MB, {len(rows)} rows parsed, {n} new benchmark NAVs")
        total += n
        start = stop + timedelta(days=1)
        time.sleep(2)   # be polite to AMFI's server
    return total


def load_into_db(path: Path = NAV_CSV, db_path: Path = DB_PATH) -> int:
    init_db(db_path)
    if not path.exists():
        return 0
    with path.open() as f, connect(db_path) as c:
        rows = [(r["scheme_code"], r["benchmark"], r["date"], float(r["nav"]), r["scheme_name"])
                for r in csv.DictReader(f)]
        c.executemany("INSERT OR REPLACE INTO fund_navs VALUES (?,?,?,?,?)", rows)
    return len(rows)


def main(mode: str) -> int:
    from v4 import alerts
    cfg = load_config()
    try:
        rows = parse_amfi(fetch_amfi())
        if mode == "discover":
            print(f"Parsed {len(rows)} fund rows from AMFI")
            for key, b in cfg.items():
                loose = [r for r in rows if re.search(b["match"], r["scheme_name"], re.I)]
                print(f"[{key}] {len(loose)} name matches before filters, e.g.:")
                for r in loose[:4]:
                    print(f"    {r['scheme_code']} | {r['scheme_name']} | {r.get('plan_option','')}")
            for key, funds in discover(rows, cfg).items():
                print(f"\n== {key} ({cfg[key]['label']}): {len(funds)} Direct-Growth funds")
                for r in funds:
                    print(f"  {r['scheme_code']} | {r['scheme_name']} | NAV {r['nav']} on {r['date']}")
            return 0
        if mode == "backfill":
            print(f"Backfill done: {backfill()} NAVs added")
            return 0
        n = record(rows, cfg)
        print(f"Recorded {n} new benchmark NAVs")
        return 0
    except Exception as e:
        alerts.send(f"❌ V4 benchmark NAV job FAILED ({mode}): {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "record"))


def composite(benchmark: str, db_path: Path = DB_PATH, base: float = 100.0) -> list[tuple[str, float]]:
    """D-122: one benchmark line = chained MEDIAN daily return of all its tracked funds.

    Plain English: each day, look at every fund that has a price today and on its
    previous recorded day, take the middle (median) of their returns, and grow the
    line by that. A fund joining, closing or missing a day doesn't break the line.
    """
    from statistics import median
    with connect(db_path) as c:
        rows = c.execute("SELECT scheme_code, date, nav FROM fund_navs WHERE benchmark=? ORDER BY date",
                         (benchmark,)).fetchall()
    last: dict[str, float] = {}
    by_date: dict[str, list[float]] = {}
    for code, date, nav in rows:
        if code in last and last[code] > 0:
            by_date.setdefault(date, []).append(nav / last[code] - 1)
        last[code] = nav
    level, line = base, []
    first = rows[0][1] if rows else None
    if first:
        line.append((first, base))
    for date in sorted(by_date):
        level *= 1 + median(by_date[date])
        line.append((date, level))
    return line
