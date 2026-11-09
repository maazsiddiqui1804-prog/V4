"""US safeguards required by D-132 before and after US buying.

Plain English — four checks, each produces warnings (never blocks, never trades):
1. LRS remittances: money sent abroad in the Indian financial year (April–March).
   Above the TCS threshold, tax is collected at source (refundable/adjustable, but cash
   is locked up). Warn when the year's total passes 80% of the threshold.
   Threshold is a PLACEHOLDER and must be re-verified before the first transfer (D-132).
2. Schedule FA log: Indian tax returns ask, per foreign holding, for the CALENDAR-year
   (Jan–Dec) initial value, peak value and closing value. Built from holdings snapshots.
3. US estate tax: non-US persons above $60k of US assets can face US estate tax.
   Warn at ~$45k of US holdings.
4. W-8BEN: the form that sets US dividend tax to the treaty rate; it lapses at the end
   of the third calendar year after signing. Remind before that.
Inputs are small CSVs Maaz (or Claude) fills in: data/us/remittances.csv
(date, inr, usd, note) and data/us/holdings_log.csv (date, ticker, qty, usd_value).
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict


def fy_of(d: dt.date) -> str:
    """Indian financial year label, e.g. 2026-11-10 → 'FY2026-27'."""
    start = d.year if d.month >= 4 else d.year - 1
    return f"FY{start}-{str(start + 1)[-2:]}"


def remittance_warnings(rows: list[dict], today: dt.date, rules: dict) -> list[str]:
    fy = fy_of(today)
    total = sum(float(r["inr"]) for r in rows if fy_of(dt.date.fromisoformat(r["date"])) == fy)
    limit = rules["tcs_threshold_inr"]
    if total >= limit:
        return [f"LRS: ₹{total:,.0f} sent abroad in {fy} — above the ₹{limit:,.0f} TCS threshold; "
                "tax is being collected at source on further transfers."]
    if total >= limit * rules["tcs_warn_fraction"]:
        return [f"LRS: ₹{total:,.0f} sent abroad in {fy} — nearing the ₹{limit:,.0f} TCS threshold."]
    return []


def schedule_fa(rows: list[dict], year: int) -> list[dict]:
    """Per ticker for one calendar year: initial (first snapshot), peak and closing (last) value in USD."""
    by = defaultdict(list)
    for r in rows:
        d = dt.date.fromisoformat(r["date"])
        if d.year == year:
            by[r["ticker"]].append((d, float(r["usd_value"])))
    out = []
    for t, vals in sorted(by.items()):
        vals.sort()
        out.append({"ticker": t, "year": year, "initial_usd": vals[0][1],
                    "peak_usd": max(v for _, v in vals), "closing_usd": vals[-1][1]})
    return out


def estate_warning(rows: list[dict], rules: dict) -> list[str]:
    if not rows:
        return []
    last = max(r["date"] for r in rows)
    total = sum(float(r["usd_value"]) for r in rows if r["date"] == last)
    if total >= rules["estate_warn_usd"]:
        return [f"US estate tax: US holdings ≈ ${total:,.0f} (warning level ${rules['estate_warn_usd']:,}; "
                "US estate tax can apply above $60,000). Decide before adding more."]
    return []


def w8ben_reminder(signed: str | None, today: dt.date, rules: dict) -> list[str]:
    if not signed:
        return ["W-8BEN not recorded as signed — submit it in Zerodha before the first US buy (T-058)."]
    s = dt.date.fromisoformat(signed)
    expires = dt.date(s.year + 3, 12, 31)
    days = (expires - today).days
    if days <= rules["w8ben_remind_days"]:
        return [f"W-8BEN expires {expires:%d %b %Y} ({max(days, 0)} days) — renew it in Zerodha."]
    return []
