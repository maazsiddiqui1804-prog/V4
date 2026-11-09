"""US section of the monthly brief.

Plain English: shows this month's US ranking (if the US jobs have produced one),
the D-132 safeguard warnings, and — until Maaz approves the US numbers (T-054) and
the transfer rhythm (T-056) — says plainly that no US orders are suggested.
A problem here never stops the India brief; it's reported as a line instead.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from v4.engines.us import compliance as cp

US_DIR = Path(__file__).resolve().parents[3] / "data" / "us"


def _rows(name: str) -> list[dict]:
    p = US_DIR / name
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f))


def section(us_cfg: dict, today: dt.date | None = None, top: int = 8) -> list[str]:
    today = today or dt.date.today()
    L = ["\n🇺🇸 US (AI sleeve):"]
    try:
        ranking = _rows("ranking.csv")
        if ranking:
            L.append("Ranking (Kite-confirmed names; ✅ passes P/E-vs-growth check):")
            for r in ranking[:top]:
                ok = "✅" if r.get("passes_guardrail") == "True" else "❌"
                L.append(f"{r['rank']:>2}. {r['ticker']} {float(r['score_total']):.0f} {ok}")
        else:
            L.append("— no US ranking yet (shortlist and Kite check pending)")
        comp = us_cfg.get("compliance", {})
        warns = (cp.remittance_warnings(_rows("remittances.csv"), today, comp)
                 + cp.estate_warning(_rows("holdings_log.csv"), comp)
                 + cp.w8ben_reminder(comp.get("w8ben_signed"), today, comp))
        L += [f"⚠️ {w}" for w in warns]
        if not us_cfg.get("approved"):
            L.append("No US orders suggested: US numbers await your approval (dashboard T-054, T-056).")
    except Exception as e:                       # never let US break the India brief
        L.append(f"⚠️ US section unavailable this month: {e}")
    return L
