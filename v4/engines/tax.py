"""India capital-gains tax ESTIMATES for listed shares (D-093, D-108 Analysis view). Not tax advice.

Plain English, per Indian financial year (April–March), for STT-paid listed shares:
- Held ≤ 12 months → short-term gain, taxed at 20%.
- Held > 12 months → long-term gain; the first ₹1.25 lakh a year is tax-free, the rest at 12.5%.
- Losses: short-term losses reduce short-term then long-term gains; long-term losses reduce only
  long-term gains. Unused losses carry forward (not modelled here).
- 4% health & education cess on top; surcharge ignored (depends on total income).
Rates are PLACEHOLDERS read from config (tax:), checked 2026-11-10 against published guides for the
Finance (No. 2) Act 2024 rates; re-verify under the Income-tax Act 2025 before the first return (D-132 review).
US shares are taxed differently (D-132 summary) and are not covered here.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

DEFAULT = {"stcg_rate": 0.20, "ltcg_rate": 0.125, "ltcg_exempt_inr": 125000, "cess": 0.04, "long_term_days": 365}


def rules_from_config() -> dict:
    import yaml
    from v4.db import ROOT
    return dict(DEFAULT, **(yaml.safe_load((ROOT / "config" / "placeholders.yaml").read_text()).get("tax") or {}))


def fy(d: dt.date) -> str:
    s = d.year if d.month >= 4 else d.year - 1
    return f"FY{s}-{str(s + 1)[-2:]}"


def estimate(sales: list[dict], rules: dict = DEFAULT) -> dict[str, dict]:
    """sales: [{buy_date, sell_date, gain}] (gain after costs, ₹). Returns per financial year."""
    by = defaultdict(lambda: {"st": 0.0, "lt": 0.0})
    for s in sales:
        b, d = dt.date.fromisoformat(s["buy_date"]), dt.date.fromisoformat(s["sell_date"])
        kind = "lt" if (d - b).days > rules["long_term_days"] else "st"
        by[fy(d)][kind] += float(s["gain"])
    out = {}
    for year, g in sorted(by.items()):
        st, lt = g["st"], g["lt"]
        if st < 0:                       # short-term loss offsets long-term gain
            lt, st = lt + st, 0.0
        if lt < 0:
            lt = 0.0                     # long-term loss can't offset short-term gain
        lt_taxable = max(0.0, lt - rules["ltcg_exempt_inr"])
        tax = (st * rules["stcg_rate"] + lt_taxable * rules["ltcg_rate"]) * (1 + rules["cess"])
        out[year] = {"short_term_gain": round(g["st"]), "long_term_gain": round(g["lt"]),
                     "taxable_short": round(st), "taxable_long": round(lt_taxable), "tax_estimate": round(tax)}
    return out
