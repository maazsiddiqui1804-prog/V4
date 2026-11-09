"""US monthly pipeline (D-133–D-136). Four stages; each can be re-run safely.

  python -m v4.jobs.us_monthly fundamentals   SEC financials for every universe name → data/us/metrics.csv
  python -m v4.jobs.us_monthly shortlist      kill filters + quality/growth → data/us/shortlist.csv (top ~40)
  python -m v4.jobs.us_monthly prices         Tiingo ~13-month history, ONLY for shortlisted names already
                                              Kite-confirmed (D-135); ≤45 per run (free plan: 50/hour)
  python -m v4.jobs.us_monthly rank           momentum + PEG guardrail → data/us/ranking.csv + Telegram

Kite confirmation lives in data/us_universe.csv, column zerodha_checked = yes / no.
Claude fills it in by searching Kite with Maaz logged in (D-133). 'no' names go on the blocklist.
While config us.approved is false, the ranking is sent but no US buy orders are produced.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
import yaml

from v4.db import ROOT
from v4.engines.us import fundamentals as fu, score as us, final as fn

US_DIR = ROOT / "data" / "us"
UNIVERSE = ROOT / "data" / "us_universe.csv"
CONFIG = ROOT / "config" / "placeholders.yaml"
TIINGO = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"


def cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text())["us"]


def read_csv(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f))


def write_csv(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys()) if rows else ["ticker"]
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def stage_fundamentals() -> str:
    uni = read_csv(UNIVERSE)
    out, missing = [], 0
    for r in uni:
        try:
            f = fu.company(int(r["cik"]))
        except requests.HTTPError:
            missing += 1
            continue
        f.pop("_currency", None)
        m = us.metrics(f)
        eps = f.get("eps_diluted", {})
        out.append({"ticker": r["ticker"], "name": r["name"], "layer": r["layer"],
                    **{k: ("" if v is None else v) for k, v in m.items()},
                    "eps": list(eps.values())[-1] if eps else "",
                    "eps_g3": fn.eps_growth_3y(eps) or "",
                    "zerodha_checked": r.get("zerodha_checked", "")})
    write_csv(US_DIR / "metrics.csv", out)
    return f"US fundamentals: {len(out)} companies read from SEC ({missing} unavailable)"


def _num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def stage_shortlist() -> str:
    c = cfg()
    df = pd.DataFrame(read_csv(US_DIR / "metrics.csv"))
    num = ["debt_equity", "interest_cover", "cash_conversion_3y", "roce_floor_3y", "rev_growth", "profit_growth"]
    df = _num(df, num)
    df["losses_3y"] = df["losses_3y"].map({"True": True, "False": False})
    rows = [{k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()}
            for r in df.to_dict("records")]
    s = us.shortlist(rows, c["kill_filters"], c["weights"], c["shortlist_size"])
    keep = s[s["shortlisted"]].drop(columns=["reasons"])
    write_csv(US_DIR / "shortlist.csv", keep.to_dict("records"))
    need = keep[keep["zerodha_checked"].fillna("") == ""]["ticker"].tolist()
    return (f"US shortlist: {len(s)} of {len(df)} pass kill filters; top {len(keep)} shortlisted. "
            f"Kite check needed for {len(need)}: {', '.join(need)}")


def tiingo_history(ticker: str, start: str) -> list[tuple[str, float]]:
    token = os.environ["TIINGO_API_KEY"]
    r = requests.get(TIINGO.format(ticker=ticker.replace(".", "-")), timeout=30,
                     params={"startDate": start, "resampleFreq": "daily"},
                     headers={"Content-Type": "application/json", "Authorization": f"Token {token}"})
    if r.status_code == 429:
        raise RuntimeError("rate-limited")
    r.raise_for_status()
    return [(x["date"][:10], float(x["adjClose"] or x["close"])) for x in r.json()]


def stage_prices(budget: int = 45) -> str:
    month = dt.date.today().strftime("%Y-%m")
    short = read_csv(US_DIR / "shortlist.csv")
    store = US_DIR / "prices.json"
    data = json.loads(store.read_text()) if store.exists() else {}
    start = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    done = skipped = 0
    for r in short:
        t = r["ticker"]
        if r.get("zerodha_checked", "").lower() != "yes":
            skipped += 1                                   # D-135: never price unconfirmed names
            continue
        if data.get(t, {}).get("month") == month:
            continue
        if budget <= 0:
            break
        try:
            hist = tiingo_history(t, start)
        except RuntimeError:
            break
        budget -= 1
        data[t] = {"month": month, **fn.returns(hist)}
        done += 1
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(data, indent=1))
    pending = [r["ticker"] for r in short if r.get("zerodha_checked", "").lower() == "yes"
               and data.get(r["ticker"], {}).get("month") != month]
    return f"US prices: {done} fetched this run; {len(pending)} still pending; {skipped} not Kite-confirmed (not priced)"


def stage_rank() -> str:
    c = cfg()
    short = pd.DataFrame(read_csv(US_DIR / "shortlist.csv"))
    prices = json.loads((US_DIR / "prices.json").read_text()) if (US_DIR / "prices.json").exists() else {}
    month = dt.date.today().strftime("%Y-%m")
    short = short[short["zerodha_checked"].str.lower() == "yes"].copy()
    for k in ("price", "ret_6m", "ret_12m"):
        short[k] = short["ticker"].map(lambda t: (prices.get(t, {}) if prices.get(t, {}).get("month") == month else {}).get(k))
    short = _num(short, ["score_quality", "score_growth", "price", "ret_6m", "ret_12m", "eps", "eps_g3"])
    ranked = fn.rank(short, c["weights"], c["max_peg"])
    write_csv(US_DIR / "ranking.csv", ranked.to_dict("records"))
    lines = [f"🇺🇸 V4 US ranking — {month} (Kite-confirmed shortlist only)"]
    for r in ranked.head(10).itertuples():
        lines.append(f"{r.rank:>2}. {r.ticker} {r.score_total:.0f} · {'✅' if r.passes_guardrail else '❌ ' + r.guardrail_reason}")
    if not c.get("approved"):
        lines.append("US numbers not yet approved (dashboard T-054): ranking only, no US orders.")
    return "\n".join(lines)


STAGES = {"fundamentals": stage_fundamentals, "shortlist": stage_shortlist,
          "prices": stage_prices, "rank": stage_rank}


def main(stage: str) -> int:
    from v4 import alerts
    try:
        msg = STAGES[stage]()
    except Exception as e:
        alerts.send(f"❌ V4 US {stage} FAILED: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print(msg)
    alerts.send(msg[:3900])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
