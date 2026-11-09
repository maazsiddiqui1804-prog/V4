"""Investment Engine, step 5: a verdict on every holding (D-027, D-028, D-061, D-127).

Plain English, checked in this order for each India holding:
1. SELL — thesis break: fails a kill filter this month (D-027).
2. SELL — quality degradation: quality score in the bottom quarter of this month's
   survivors (D-127).
3. SELL — ranked below 100 this month AND last month (D-027).
   WATCH — below 100 this month only: sells next month if still below.
4. REVIEW — an unreviewed red-flag filing (D-061): no automatic sell; buying of
   this stock is frozen until Maaz reviews the filing.
5. TRIM — worth more than 2× its target weight (1/15): sell back down to 2× (D-028, D-127).
6. HOLD — otherwise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


@dataclass
class Verdict:
    symbol: str
    security_id: int
    action: str        # SELL / WATCH / REVIEW / TRIM / HOLD
    reason: str
    shares: int = 0    # shares to sell for SELL (all) or TRIM (excess)


def verdicts(holdings: pd.DataFrame, filters: pd.DataFrame, ranked: pd.DataFrame,
             prev_rank: dict, red_flag_ids: set, rules: dict) -> list[Verdict]:
    """holdings: security_id, symbol, quantity, current_price.
    filters: security_id, passed, reasons (this month's kill-filter results).
    ranked: security_id, rank, score_quality (this month's survivors).
    prev_rank: {security_id: rank last month}; missing = not ranked last month."""
    out: list[Verdict] = []
    if not len(holdings):
        return out
    target_n = rules["target_holdings"]
    max_rank = rules["max_rank"]
    trim_at = rules["trim_above_x_target"]
    trim_to = rules["trim_to_x_target"]
    q_cut = rules["quality_bottom_fraction"]

    total = float((holdings["quantity"] * holdings["current_price"]).sum())
    target_value = total / target_n
    f = filters.set_index("security_id")
    rk = ranked.set_index("security_id")
    q_pct = ranked.set_index("security_id")["score_quality"].rank(pct=True) if len(ranked) else pd.Series(dtype=float)

    for h in holdings.itertuples():
        sid, qty, px = int(h.security_id), int(h.quantity), float(h.current_price)
        value = qty * px
        if sid in f.index and not bool(f.loc[sid, "passed"]):
            reasons = f.loc[sid, "reasons"]
            reasons = "; ".join(reasons) if isinstance(reasons, list) else reasons
            out.append(Verdict(h.symbol, sid, "SELL", f"thesis break: {reasons}", qty))
            continue
        if sid not in f.index:
            out.append(Verdict(h.symbol, sid, "SELL", "no longer in the investable universe (left Nifty 500 or excluded)", qty))
            continue
        if sid in q_pct.index and q_pct[sid] <= q_cut:
            out.append(Verdict(h.symbol, sid, "SELL", "quality degradation: bottom quarter of quality scores", qty))
            continue
        rank_now = int(rk.loc[sid, "rank"]) if sid in rk.index else None
        if rank_now is not None and rank_now > max_rank:
            if prev_rank.get(sid, 0) > max_rank:
                out.append(Verdict(h.symbol, sid, "SELL", f"ranked below {max_rank} two months running (now {rank_now})", qty))
            else:
                out.append(Verdict(h.symbol, sid, "WATCH", f"rank {rank_now}: sells next month if still below {max_rank}"))
            continue
        if sid in red_flag_ids:
            out.append(Verdict(h.symbol, sid, "REVIEW", "red-flag filing: review it; buying this stock is frozen"))
            continue
        if total > 0 and value > trim_at * target_value:
            excess = value - trim_to * target_value
            shares = int(math.floor(excess / px))
            if shares > 0:
                out.append(Verdict(h.symbol, sid, "TRIM",
                                   f"{value / total:.0%} of V4 vs target {1 / target_n:.0%}: trim back to {trim_to:g}× target",
                                   shares))
                continue
        out.append(Verdict(h.symbol, sid, "HOLD", f"rank {rank_now}"))
    return out
