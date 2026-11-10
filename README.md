# V4

Maaz's personal rules-based investing and trading system. Private.

- **Rules:** `docs/V4_Decisions_Log.md` (authority) · **Where the build is:** `docs/V4_Status.md` · **How Claude works here:** `CLAUDE.md`
- **App:** https://investing-trading.streamlit.app/ (private; `dashboard/app.py`, reads `data/app/`)
- **Telegram:** every message from V4 ends with the app link.

The system screens, scores and signals. It never places orders; Maaz decides and executes.

## Where things live
| What | Where |
|---|---|
| Settings and starting numbers | `config/placeholders.yaml` (all placeholders until proven), `config/us_universe.yaml`, `config/benchmarks.yaml`, `config/app.yaml` |
| Shared database | `data/v4.sqlite` (only the cloud writes it) |
| App snapshot (prices, signals, job status, build copy) | `data/app/` — refreshed weekdays 18:13 IST |
| Full daily price history | branch `prices` (one commit, replaced daily — keeps main small) |
| Strategy research data (15 years) | branch `research-data`; method and results in `research/2026-11-strategy-search/` |
| Scheduled jobs | `.github/workflows/` — every job alerts Telegram on failure; Monday check catches silent jobs |

## Engines (current rules)
- **India investing:** monthly; Nifty 500 ex financials; kill filters → quality/growth/momentum score → P/E guardrail → buy plan (D-123–D-127). First real list December 2026.
- **US investing:** AI-chain US companies ≥ $10B on Zerodha; SEC fundamentals → shortlist → Kite check → momentum + P/E-to-growth (D-133–D-136). Waiting on Kite check and approvals.
- **India trading ("B2", D-137):** 52-week-high breakout on volume, top-20% strength, only in a healthy market; 2×ATR stop; exit on a close below the 50-day average. Watch-only now; paper after the GMAT; live only after the D-048 bar. Capital 10% → up to 30% as it proves itself (D-100).
