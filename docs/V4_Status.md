# V4 Status

**Last updated:** 2026-11-09 · **Phase:** Build — India Investment Engine (all steps built except red-flag alerts)

## Next session
1. Red-flag filing alerts (T-026, D-061/D-109): find a reliable official source for NSE/BSE announcements (checked live), checks ~3× a day in market hours, Telegram alert + freeze buying.
2. First real monthly brief: freezes November's list (D-063) — Maaz to say go (T-029 sign-off on starting numbers), then first buys (T-030).
3. Known gap for first quarterly review: Screener's 5/10-yr averages cover fewer years for recent listings.

## Where we are
- Repo live and private: github.com/maazsiddiqui1804-prog/v4. Claude GitHub App installed on this repo only.
- Accounts done: GitHub, Kite Personal API app (free), Telegram bot "V4 Alerts", all 4 GitHub Secrets.
- Cloud → phone proven: Health check sends Telegram "V4 is alive" (confirmed 2026-11-09).
- India data: NSE Nifty 500 list matched 500/500 to Screener by ISIN. 78 banks/NBFCs/insurers and 3 REITs excluded → **419 investable**. All required columns present (D-116 loss filter columns included).
- Monthly routine live (D-118): drop Screener export in data/inbox on github.com → cloud imports, archives, reports to Telegram. Tested end to end 2026-11-09 (NSE list fetched from the cloud).
- Benchmarks live (D-121/D-122): 21 index funds from AMFI recorded every weekday 22:47 IST; first record 2026-11-09 (NAV date 2026-11-06). Benchmark history starts here (forward-tracking, D-063).
- All 3 cloud jobs alert Telegram on failure; workflow building blocks on v6 (Node 24). 
- Holdings importer built (D-119) from a sample Console file Maaz supplied: drop the holdings XLSX in data/inbox (alone or with the Screener export). Raw file is deleted after import, never archived (contains client ID). Account is V4-only (D-120), currently empty. 39 automated checks pass.
- Investment Engine steps 1–3 built and tested on real data (preview only, nothing frozen): kill filters (D-123: 254 of 419 pass), score (D-124; regime = normal on 2026-11-09, Nifty 500 line 101.8 vs 200-day 98.3), India guardrail (D-125: 8 of top 20 buyable), monthly buy plan (D-126), sell/trim/watch/review verdicts (D-127), monthly Telegram brief with list freezing (runs automatically after each monthly import; re-run with another amount reuses the frozen list). Dry run on 2026-11-09 data at ₹25k: BUY MCX 3 shares, IGIL 29 shares (preview only, not frozen). Benchmark history backfilled from AMFI to 2025-09-15 (5,592 NAVs). 82 automated checks pass.
- No numbers proven; all cut-offs are placeholders.

## Open items

| Item | When |
|---|---|
| Starting placeholder numbers set (D-123–D-125); formal sign-off before first buys | T-029 |
| Kite login page: needed only for the Trading Engine (Kite Connect); redirect URL still a placeholder | Trading Engine build |
| US tax / estate tax / disclosure on GIFT City route (blocks US *buying* only, D-085) | Before first US buy |
| Confirm US universe limited to Zerodha-tradable list (D-022) | Build: US module |
| Trading placeholder numbers (liquidity floor, volume multiple, stretch limit, trail method) | Trading Engine build (T-047) |

## Build plan
- **Until GMAT (~28 Nov):** D-087 pace 3–4 hrs/week; Maaz chose extra time on 2026-11-09. Data layer (India) done.
- **Next / after GMAT, 8–10 hrs/week:**
  1. India Investment Engine + red-flag alerts → first monthly top 20 (real money via monthly additions).
  2. US AI module (SEC EDGAR + Tiingo) + combined caps.
  3. Trading Engine backtest → daily paper signals (₹1L notional); Kite Connect + login page.
  4. Dashboard (Streamlit, D-112), quarterly report, warning checks, fix buffer.

## Fixed clocks after build
- Trading paper gate: ≥3 months + ≥30 trades + ≥0.3R avg net.
- Investment: 12-month warning review; 3-year kill test vs Nifty 500 and Nifty200 Quality 30 (index-fund median, D-121/D-122).
- Reviews: quarterly (Jan/Apr/Jul/Oct); annual strategy review in January.

## Session log
- **2026-10-24:** Brief absorbed. Build order, data, outputs, news-as-risk-filter decided.
- **2026-10-25:** Philosophy rethink, US/AI added, Kite Connect chosen, strategy for both engines, all flaw fixes, review calendar, build plan B. Docs created.
- **2026-11-08:** Build start moved to 2026-11-09 (D-086). Final open items closed (D-087–D-098). Amendments D-099–D-102, optimisation D-103–D-107, dashboard D-108, midday alerts D-109, GTT stops D-110. V4 Dashboard created and pinned (https://claude.ai/artifact/NP2ZkpE47Hp3F6FY7SAs1S).
- **2026-11-09:** Build started. SQLite in repo (D-111), Streamlit hosting (D-112). Accounts, secrets, repo skeleton, Telegram alerts, cloud health check. Screener Premium as source (D-113); importer built, 500/500 matched; exclusions narrowed to banks/NBFCs/insurers (D-114) and REITs (D-115); loss filter defined (D-116); Project docs master (D-117). Extra evening block (~5–6 hrs total, above D-087 pace by Maaz's choice): monthly inbox routine (D-118), holdings from Console XLSX (D-119), account V4-only (D-120), benchmarks from AMFI index-fund NAVs as median of funds (D-121, D-122); holdings importer built from a sample Console file. Investment Engine steps 1–3: kill filters (D-123), score (D-124, with AMFI history backfill for the regime signal), India guardrail (D-125). Then buy plan (D-126), sell rules (D-127), monthly brief + freeze. Bugs caught and fixed: AMFI history column names; top-ups never triggering; rounding breaking the ₹10k minimum. Workflow YAML bug found and fixed; checks now require every workflow to parse and alert on failure.
