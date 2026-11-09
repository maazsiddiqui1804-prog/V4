"""Investment Engine reviews: 12-month warning (D-065) and 3-year kill test (D-064).

Plain English: the fair comparison for monthly investing is "what if every rupee I put into V4 had
gone into the benchmark index fund on the same day instead?" (a shadow portfolio). V4's sleeve
value already has costs taken out; taxes V4 paid on sells are added as extra money taken out,
so the comparison is after costs and tax (D-064). Benchmarks = index-fund median lines (D-121/D-122):
Nifty 500 and Nifty200 Quality 30.
- 12 months: lagging BOTH → deep review (no automatic switch, D-065).
- 36 months: must beat BOTH, else the kill test fails → switch to index funds (Maaz decides).
"""
from __future__ import annotations

import bisect
import datetime as dt


def shadow_value(contributions: list[tuple[str, float]], line: dict[str, float], on: str) -> float:
    """Value on `on` if each contribution (date, ₹) had bought the benchmark line that day
    (or the next day the line has a value)."""
    dates = sorted(line)
    def level(d: str, after: bool) -> float:
        i = bisect.bisect_left(dates, d) if after else bisect.bisect_right(dates, d) - 1
        i = min(max(i, 0), len(dates) - 1)
        return line[dates[i]]
    end = level(on, after=False)
    return sum(amt * end / level(d, after=True) for d, amt in contributions)


def verdict(start: str, today: str, sleeve_value: float, taxes_paid: float,
            contributions: list[tuple[str, float]], lines: dict[str, dict[str, float]]) -> dict:
    months = (dt.date.fromisoformat(today) - dt.date.fromisoformat(start)).days / 30.44
    v4 = sleeve_value                       # taxes already left the account; shadow funds paid none yet
    shadows = {name: shadow_value(contributions, line, today) for name, line in lines.items()}
    beats = {name: v4 > s for name, s in shadows.items()}
    out = {"months": round(months, 1), "v4": round(v4), "taxes_paid": round(taxes_paid),
           "shadows": {k: round(v) for k, v in shadows.items()}, "beats": beats, "stage": "tracking", "action": ""}
    if months >= 36:
        out["stage"] = "kill test (D-064)"
        out["action"] = ("PASS — keep V4" if all(beats.values())
                         else "FAIL — V4 did not beat " + " and ".join(k for k, b in beats.items() if not b)
                         + " after costs and tax: switch this sleeve to index funds (your decision)")
    elif months >= 12:
        out["stage"] = "12-month warning (D-065)"
        out["action"] = ("Lagging both benchmarks — deep review (no automatic switch)" if not any(beats.values())
                         else "OK — not lagging both")
    return out
