# V4 Status

**Last updated:** 2026-11-09 · **Phase:** Build — data layer done (India); next: India Investment Engine

## Next session
1. India Investment Engine (T-021 onward): kill filters, score (quality/growth/momentum + regime switch), India guardrail, portfolio builder, sell rules, monthly brief. Starting placeholder numbers need Maaz's approval (T-029).
2. Holdings importer: build when the first V4 buys produce a real Console XLSX (D-119).
3. Check the daily benchmark NAV job keeps recording (it alerts Telegram on failure).

## Where we are
- Repo live and private: github.com/maazsiddiqui1804-prog/v4. Claude GitHub App installed on this repo only.
- Accounts done: GitHub, Kite Personal API app (free), Telegram bot "V4 Alerts", all 4 GitHub Secrets.
- Cloud → phone proven: Health check sends Telegram "V4 is alive" (confirmed 2026-11-09).
- India data: NSE Nifty 500 list matched 500/500 to Screener by ISIN. 78 banks/NBFCs/insurers and 3 REITs excluded → **419 investable**. All required columns present (D-116 loss filter columns included).
- Monthly routine live (D-118): drop Screener export in data/inbox on github.com → cloud imports, archives, reports to Telegram. Tested end to end 2026-11-09 (NSE list fetched from the cloud).
- Benchmarks live (D-121/D-122): 21 index funds from AMFI recorded every weekday 22:47 IST; first record 2026-11-09 (NAV date 2026-11-06). Benchmark history starts here (forward-tracking, D-063).
- All 3 cloud jobs alert Telegram on failure; workflow building blocks on v6 (Node 24). 34 automated checks pass.
- Holdings: account is V4-only (D-120), currently empty; importer deferred until first buys (D-119).
- Nothing scored yet. No numbers proven.

## Open items

| Item | When |
|---|---|
| Starting placeholder numbers (filter cut-offs, valuation margins, momentum lookback) | Investment Engine build (T-029) |
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
- **2026-11-09:** Build started. SQLite in repo (D-111), Streamlit hosting (D-112). Accounts, secrets, repo skeleton, Telegram alerts, cloud health check. Screener Premium as source (D-113); importer built, 500/500 matched; exclusions narrowed to banks/NBFCs/insurers (D-114) and REITs (D-115); loss filter defined (D-116); Project docs master (D-117). Extra evening block (~5–6 hrs total, above D-087 pace by Maaz's choice): monthly inbox routine (D-118), holdings from Console XLSX (D-119), account V4-only (D-120), benchmarks from AMFI index-fund NAVs as median of funds (D-121, D-122). Workflow YAML bug found and fixed; checks now require every workflow to parse and alert on failure.
