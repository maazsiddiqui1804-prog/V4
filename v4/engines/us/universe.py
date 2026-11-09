"""US AI value-chain universe (D-022, D-133, D-134). Rule lives in config/us_universe.yaml.

Plain English, three steps (all official/free data):
1. Size pre-filter: SEC's one-shot list of every filer's reported public float
   (market value of shares held by outsiders). Keep floats ≥ half the floor, so
   only plausible large caps get priced (Tiingo's free plan allows 500 symbols/month).
   Foreign filers (20-F, e.g. TSMC, ASML) don't report float; they're kept for step 3.
2. Industry + exchange: SEC industry code in the approved list, listed on NYSE/Nasdaq.
3. Market value = SEC shares outstanding × latest Tiingo price ≥ the floor.
   (For ADRs this can overstate size; such names are far above the floor anyway.)
Output: data/us_universe.csv. Price performance never decides membership.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import requests
import yaml

from v4.db import ROOT
from v4.importers import sec

CONFIG = ROOT / "config" / "us_universe.yaml"
OUT = ROOT / "data" / "us_universe.csv"
FRAME = "https://data.sec.gov/api/xbrl/frames/dei/EntityPublicFloat/USD/{period}.json"
SHARES = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/EntityCommonStockSharesOutstanding.json"
TIINGO = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"


def load_rule(path: Path = CONFIG) -> dict:
    rule = yaml.safe_load(path.read_text())
    rule["sic_all"] = {int(c) for codes in rule["sic_codes"].values() for c in codes}
    return rule


def public_floats(periods: list[str]) -> dict[int, float]:
    """Latest reported public float per company (CIK), from SEC 'frames'."""
    out: dict[int, float] = {}
    for p in periods:                       # oldest first, so newer values overwrite
        try:
            data = sec.get(FRAME.format(period=p))
        except requests.HTTPError:
            continue
        for row in data.get("data", []):
            out[int(row["cik"])] = float(row["val"])
    return out


def shares_outstanding(cik: int) -> float | None:
    """Total shares on the latest cover-page date (summing share classes)."""
    try:
        data = sec.get(SHARES.format(cik=cik))
    except requests.HTTPError:
        return None
    facts = data.get("units", {}).get("shares", [])
    if not facts:
        return None
    latest = max(f["end"] for f in facts)
    return float(sum(f["val"] for f in facts if f["end"] == latest))


def tiingo_close(ticker: str) -> float | None:
    token = os.environ.get("TIINGO_API_KEY", "").strip()
    if not token:
        raise RuntimeError("TIINGO_API_KEY is not set (add it as a GitHub Secret)")
    r = requests.get(TIINGO.format(ticker=ticker.replace(".", "-")), timeout=30,
                     headers={"Content-Type": "application/json", "Authorization": f"Token {token}"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    rows = r.json()
    return float(rows[-1]["adjClose"] or rows[-1]["close"]) if rows else None


def passes_industry(profile: dict, rule: dict) -> bool:
    try:
        sic = int(profile.get("sic") or 0)
    except ValueError:
        return False
    ex = {e.strip() for e in (profile.get("exchanges") or "").split(",")}
    return sic in rule["sic_all"] and bool(ex & set(rule["exchanges"]))


def build(periods: list[str]) -> tuple[list[dict], dict]:
    rule = load_rule()
    floor = float(rule["min_market_cap_usd"])
    blocked = set(rule.get("zerodha_blocklist") or [])
    tmap = sec.ticker_map()                       # ticker -> CIK
    by_cik: dict[int, list[str]] = {}
    for t, c in tmap.items():
        by_cik.setdefault(c, []).append(t)
    floats = public_floats(periods)

    stats = {"sec_tickers": len(tmap), "companies": len(by_cik), "after_float": 0,
             "after_industry": 0, "priced": 0, "in_universe": 0, "blocked": 0}
    rows = []
    for cik, tickers in by_cik.items():
        f = floats.get(cik)
        if f is not None and f < floor / 2:
            continue
        stats["after_float"] += 1
        prof = sec.profile(cik)
        if not passes_industry(prof, rule):
            continue
        stats["after_industry"] += 1
        ticker = sorted(tickers, key=len)[0]      # primary ticker (shortest)
        shares = shares_outstanding(cik)
        price = tiingo_close(ticker) if shares else None
        if not (shares and price):
            continue
        stats["priced"] += 1
        mcap = shares * price
        if mcap < floor:
            continue
        if ticker in blocked:
            stats["blocked"] += 1
            continue
        layer = next(k for k, codes in rule["sic_codes"].items() if int(prof["sic"]) in codes)
        rows.append({"ticker": ticker, "cik": cik, "name": prof["name"], "sic": prof["sic"],
                     "layer": layer, "exchange": prof["exchanges"], "market_cap_usd": round(mcap),
                     "price": price, "shares": round(shares), "zerodha_checked": ""})
    rows.sort(key=lambda r: -r["market_cap_usd"])
    stats["in_universe"] = len(rows)
    return rows, stats


def save(rows: list[dict], path: Path = OUT) -> None:
    """Keep earlier Kite-check marks for names already in the file."""
    checked = {}
    if path.exists():
        with path.open() as f:
            checked = {r["ticker"]: r.get("zerodha_checked", "") for r in csv.DictReader(f)}
    for r in rows:
        r["zerodha_checked"] = checked.get(r["ticker"], "")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["ticker"])
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    from v4 import alerts
    import datetime as dt
    y = dt.date.today().year
    periods = [f"CY{y - 2}Q2I", f"CY{y - 1}Q2I", f"CY{y}Q2I"]
    try:
        rows, stats = build(periods)
        save(rows)
        layers = {}
        for r in rows:
            layers[r["layer"]] = layers.get(r["layer"], 0) + 1
        msg = (f"🇺🇸 V4 US universe built: {stats['in_universe']} companies ≥ $10B "
               f"({', '.join(f'{k} {v}' for k, v in sorted(layers.items()))}). "
               f"Screened {stats['companies']} SEC companies → {stats['after_float']} after size pre-filter → "
               f"{stats['after_industry']} in AI industry codes → {stats['priced']} priced. Not yet Kite-checked.")
        print(msg)
        for r in rows:
            print(f"  {r['ticker']:6} {r['layer']:20} ${r['market_cap_usd'] / 1e9:,.0f}B  {r['name']}")
        alerts.send(msg)
        return 0
    except Exception as e:
        alerts.send(f"❌ V4 US universe build FAILED: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
