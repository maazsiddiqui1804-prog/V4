# V4 Status

**Last updated:** 2026-11-09 · **Phase:** Build — India Investment Engine code complete; first real brief December 2026 (D-129)

## Next session
1. **Before the first brief (December, after GMAT):** quick review together of a fresh dry run on December data; formal sign-off of starting numbers D-123–D-127 (T-029). Then Maaz drops the December Screener export in the GitHub inbox → brief arrives on Telegram → first buys (T-030).
2. Then Phase 3: US AI module (Zerodha-tradable list, SEC EDGAR, Tiingo, universe rule, US guardrail, Nasdaq-100 fallback, combined caps; US tax check before any US buy).
3. Known gaps for the first quarterly review: (a) Screener's 5/10-yr averages cover fewer years for recent listings; (b) red-flag name matching depends on NSE's company names lining up with the Nifty 500 list.

## Where we are
- Repo (private): github.com/maazsiddiqui1804-prog/v4. Claude GitHub App on this repo only. 100 automated checks pass.
- **Running automatically:** benchmark fund NAVs weekdays 22:47 IST; red-flag checks weekdays 10:47 / 13:17 / 15:23 IST (watchlist empty until the first list or holdings); monthly import whenever a file lands in data/inbox; monthly brief right after a successful import (guarded: none before 2026-12). Every job alerts Telegram on failure.
- **India data:** 500/500 Nifty 500 matched; 78 banks/NBFCs/insurers and 3 REITs excluded → 419 investable (D-113–D-115). Screener column list updated by Claude in Maaz's Chrome (profit years, cash-flow preceding year; 5 unused columns removed).
- **Benchmarks:** median of 21 AMFI index funds (D-121/D-122), history from 2025-09-15.
- **Holdings:** Console XLSX via inbox (D-119); account is V4-only (D-120) and empty.
- **Investment Engine (all 8 steps built, D-123–D-128):** kill filters → score (regime-aware) → India guardrail → buy plan → holding verdicts → red flags → monthly brief → frozen list. Dry run on 2026-11-09 data at ₹25k: BUY MCX 3 shares, IGIL 29 shares (preview only — nothing frozen, nothing sent).
- No numbers proven; all cut-offs are placeholders.

## Open items

| Item | When |
|---|---|
| Formal sign-off of starting numbers (T-029) and first buys (T-030) | December brief |
| US tax / estate tax / disclosure on GIFT City route (blocks US *buying* only, D-085) | Before first US buy |
| Confirm US universe limited to Zerodha-tradable list (D-022) | Phase 3 |
| Kite login page (Kite Connect) | Phase 4 |
| Trading placeholder numbers (liquidity floor, volume multiple, stretch limit, trail method) | Phase 4 (T-047) |

## Build plan
- **Until GMAT (~28 Nov):** no build work needed; jobs run on their own.
- **After GMAT, 8–10 hrs/week:**
  1. December: first real brief + buys (Phase 2 close).
  2. US AI module (SEC EDGAR + Tiingo) + combined caps.
  3. Trading Engine backtest → daily paper signals (₹1L notional); Kite Connect + login page.
  4. Dashboard (Streamlit, D-112), quarterly report, warning checks, fix buffer.

## Fixed clocks after build
- Trading paper gate: ≥3 months + ≥30 trades + ≥0.3R avg net.
- Investment: 12-month warning review; 3-year kill test vs Nifty 500 and Nifty200 Quality 30 (index-fund median, D-121/D-122). Forward-tracking starts with the December 2026 list.
- Reviews: quarterly (Jan/Apr/Jul/Oct); annual strategy review in January.

## Session log
- **2026-10-24:** Brief absorbed. Build order, data, outputs, news-as-risk-filter decided.
- **2026-10-25:** Philosophy rethink, US/AI added, Kite Connect chosen, strategy for both engines, all flaw fixes, review calendar, build plan B. Docs created.
- **2026-11-08:** Build start moved to 2026-11-09 (D-086). Final open items closed (D-087–D-098). Amendments D-099–D-102, optimisation D-103–D-107, dashboard D-108, midday alerts D-109, GTT stops D-110. V4 Dashboard created and pinned (https://claude.ai/artifact/NP2ZkpE47Hp3F6FY7SAs1S).
- **2026-11-09 (long session, ~6 hrs by Maaz's choice, above D-087 pace):** Accounts, repo, Telegram alerts, cloud jobs. India data layer: Screener import (D-113–D-116), Project docs master (D-117), monthly inbox routine (D-118), holdings from Console XLSX (D-119/D-120), benchmarks from AMFI index funds (D-121/D-122). India Investment Engine fully built: kill filters (D-123), score (D-124), guardrail (D-125), buy plan (D-126), sell rules (D-127), red flags from NSE RSS (D-128), monthly brief + freeze; first real brief December (D-129). Bugs found and fixed along the way: workflow YAML, AMFI history columns, top-ups never triggering, rounding below ₹10k minimum, NSE feed cut off/malformed, duplicate feed items.
