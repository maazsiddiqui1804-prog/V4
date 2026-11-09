"""Investment Engine, step 3: India valuation guardrail (D-025, D-125). Not part of the score.

Plain English:
- Buy-below price = the price at which the stock's P/E would equal its own
  10-year typical P/E plus a margin (20% to start). Above that price, don't buy.
      buy_below = price × (10-yr P/E × (1 + margin)) ÷ current P/E
  If the 10-year figure is blank, the 5-year one is used.
- Second check: P/E vs growth (PEG) must be at or below the cap (2.0 to start).
  A blank or negative PEG fails (never buy what can't be checked).
- A stock passes only if it's below its buy-below price AND passes the PEG check.
"""
from __future__ import annotations

import pandas as pd


def apply(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    out = df.copy()
    basis = out.get(rules.get("india_pe_basis", "historical_pe_10years"))
    if "historical_pe_5years" in out:
        basis = basis.fillna(out["historical_pe_5years"]) if basis is not None else out["historical_pe_5years"]
    pe, price = out["price_to_earning"], out["current_price"]
    usable = (pe > 0) & (basis > 0) & price.notna()
    out["buy_below"] = (price * basis * (1 + rules["india_pe_margin"]) / pe).where(usable).round(2)
    out["peg_ok"] = (out["peg_ratio"] > 0) & (out["peg_ratio"] <= rules["india_max_peg"])
    out["price_ok"] = usable & (price <= out["buy_below"])
    out["passes_guardrail"] = out["price_ok"] & out["peg_ok"]

    def why(r):
        if r.passes_guardrail:
            return ""
        bits = []
        if not r.price_ok:
            bits.append("no usable P/E history" if pd.isna(r.buy_below)
                        else f"price {r.current_price:,.0f} above buy-below {r.buy_below:,.0f}")
        if not r.peg_ok:
            bits.append("PEG missing or negative" if pd.isna(r.peg_ratio) or r.peg_ratio <= 0
                        else f"PEG {r.peg_ratio:.1f} > {rules['india_max_peg']}")
        return "; ".join(bits)

    out["guardrail_reason"] = out.apply(why, axis=1)
    return out
