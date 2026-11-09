# V4 Status

**Last updated:** 2026-11-09 · **Phase:** Build — Setup + data layer (sprint week 1)

## Next session — sprint week 1, part 2
Pace until GMAT: 3–4 hrs/week (D-087).
1. Maaz: add 3 missing column groups to the `V4 monthly` Screener screen and re-export — net profit for last 3 years, average ROCE 5/10 yrs, historical P/E 5/10 yrs. Without them the loss filter (D-023), quality consistency (D-024) and India buy-below price (D-025) can't run.
2. Re-import with the new export; confirm the importer report shows no missing columns.
3. Holdings sync via Kite Personal API (T-018): design the login handoff (redirect URL is a placeholder).
4. Benchmark index data (T-019) and job-failure alerts (rest of T-020).
5. Housekeeping: update GitHub workflow building blocks off Node 20 (versions to be checked live).

## Where we are
- Repo live and private: github.com/maazsiddiqui1804-prog/v4. Claude GitHub App installed on this repo only.
- Accounts done: GitHub, Kite Personal API app (free), Telegram bot "V4 Alerts", all 4 GitHub Secrets.
- Cloud → phone proven: Health check job runs the checks in GitHub Actions and sends Telegram "V4 is alive" (confirmed received 2026-11-09).
- India data: first import 2026-11-09. NSE Nifty 500 list (500 real members) matched 500/500 to the Screener export by ISIN. 78 banks/NBFCs/insurers and 3 REITs excluded → **419 investable**. 15 automated checks pass.
- Nothing scored yet. No numbers proven.

## Open items

| Item | When |
|---|---|
| Screener export missing 3 column groups (see next session #1) | Next session |
| Kite login handoff for holdings sync: redirect URL is a placeholder (127.0.0.1); likely the Streamlit dashboard later | Build: holdings sync (T-018) |
| US tax / estate tax / disclosure on GIFT City route (blocks US *buying* only, D-085) | Before first US buy |
| Confirm US universe limited to Zerodha-tradable list (D-022) | Build: US module |
| Placeholder numbers (filter cut-offs, valuation margins, liquidity floor, volume multiple, stretch limit, trail method) | Set during build as starting values; tested after |
| Repo docs/ vs Project docs: Project stays the authority; docs/ in repo is a copy refreshed at session end (assumed; Maaz to confirm) | Next session |

## Build plan
- **Until GMAT (~28 Nov), 3–4 hrs/week:** setup + data layer.
- **After GMAT, 8–10 hrs/week:**
  1. India Investment Engine + red-flag alerts → first monthly top 20 (real money via monthly additions).
  2. US AI module (SEC EDGAR + Tiingo) + combined caps.
  3. Trading Engine backtest → daily paper signals (₹1L notional).
  4. Dashboard (Streamlit, D-112), quarterly report, warning checks, fix buffer.

## Fixed clocks after build
- Trading paper gate: ≥3 months + ≥30 trades + ≥0.3R avg net.
- Investment: 12-month warning review; 3-year kill test vs Nifty 500 TRI and Nifty200 Quality 30 TRI.
- Reviews: quarterly (Jan/Apr/Jul/Oct); annual strategy review in January.

## Session log
- **2026-10-24:** Brief absorbed. Build order, data, outputs, news-as-risk-filter decided.
- **2026-10-25:** Philosophy rethink, US/AI added, Kite Connect chosen, strategy for both engines, all flaw fixes, review calendar, build plan B. Docs created.
- **2026-11-08:** Build start moved to 2026-11-09 (D-086). Final open items closed (D-087–D-098). Amendments D-099–D-102, optimisation D-103–D-107, dashboard D-108, midday alerts D-109, GTT stops D-110. V4 Dashboard created and pinned (https://claude.ai/artifact/NP2ZkpE47Hp3F6FY7SAs1S).
- **2026-11-09:** Build started. SQLite in repo (D-111), Streamlit hosting (D-112). All accounts and secrets set up; repo skeleton, Telegram alert sender and cloud health check pushed (phone alert confirmed). Screener Premium confirmed as source (D-113). Monthly India importer built; first import 500/500 matched. Financial exclusion narrowed to banks/NBFCs/insurers (D-114, 419 investable) and REITs excluded (D-115). Screener export needs 3 more column groups.
