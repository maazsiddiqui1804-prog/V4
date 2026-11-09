"""Combined caps across India + US investing (D-060, D-089).

Plain English:
- D-060: no single stock above 10% of V4, no sector above 25% (all holdings, in rupees).
- D-089: US/AI holdings at most 30% of the investment sleeve.
us_headroom() says how many rupees can go to US buys this month without breaking 30%.
check() lists any current breaches so the brief can show them (warnings; sells follow D-127 rules).
US values are converted to rupees with the given USD/INR rate.
"""
from __future__ import annotations

from collections import defaultdict


def to_inr(holdings: list[dict], usdinr: float) -> list[dict]:
    """holdings: [{name, sector, market: 'IN'|'US', value}] value in INR for IN, USD for US."""
    return [{**h, "inr": h["value"] * (usdinr if h["market"] == "US" else 1.0)} for h in holdings]


def us_headroom(holdings: list[dict], usdinr: float, new_cash_inr: float, us_cap: float = 0.30) -> float:
    h = to_inr(holdings, usdinr)
    total = sum(x["inr"] for x in h) + new_cash_inr
    us = sum(x["inr"] for x in h if x["market"] == "US")
    return max(0.0, min(new_cash_inr, us_cap * total - us))


def check(holdings: list[dict], usdinr: float, stock_cap=0.10, sector_cap=0.25, us_cap=0.30,
          min_holdings: int = 10) -> list[str]:
    h = to_inr(holdings, usdinr)
    total = sum(x["inr"] for x in h)
    if total <= 0:
        return []
    out = []
    us = sum(x["inr"] for x in h if x["market"] == "US")
    if us / total > us_cap:
        out.append(f"US share {us / total:.0%} > {us_cap:.0%} cap (D-089)")
    if len(h) < min_holdings:            # D-126: % caps apply from 10 holdings
        return out
    for x in h:
        if x["inr"] / total > stock_cap:
            out.append(f"{x['name']} {x['inr'] / total:.0%} > {stock_cap:.0%} stock cap (D-060)")
    sec = defaultdict(float)
    for x in h:
        sec[x["sector"]] += x["inr"]
    for s, v in sorted(sec.items()):
        if v / total > sector_cap:
            out.append(f"Sector {s} {v / total:.0%} > {sector_cap:.0%} cap (D-060)")
    return out
