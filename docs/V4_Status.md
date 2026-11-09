# V4 Status

**Last updated:** 2026-11-09 · **Phase:** Build — Setup + data layer (sprint week 1)

## Next session — sprint week 1, part 2
Pace until GMAT: 3–4 hrs/week (D-087).
1. Monthly export flow: pick up the Screener export straight from Maaz's laptop (device link) instead of chat attachments; design the monthly routine.
2. Holdings sync via Kite Personal API (T-018): design the login handoff (redirect URL is a placeholder).
3. Benchmark index data (T-019) and job-failure alerts (rest of T-020).
4. Housekeeping: update GitHub workflow building blocks off Node 20 (versions to be checked live).

## Where we are
- Repo live and private: github.com/maazsiddiqui1804-prog/v4. Claude GitHub App installed on this repo only.
- Accounts done: GitHub, Kite Personal API app (free), Telegram bot "V4 Alerts", all 4 GitHub Secrets.
- Cloud → phone proven: Health check job runs the checks in GitHub Actions and sends Telegram "V4 is alive" (confirmed received 2026-11-09).
- India data: first import 2026-11-09. NSE Nifty 500 list (500 real members) matched 500/500 to the Screener export by ISIN. 78 banks/NBFCs/insurers and 3 REITs excluded → **419 investable**. 15 automated checks pass.
- Nothing scored yet. No numbers proven.

## Open items

| Item | When |
|---|---|
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
- **2026-11-09:** Build started. SQLite in repo (D-111), Streamlit hosting (D-112). All accounts and secrets set up; repo skeleton, Telegram alert sender and cloud health check pushed (phone alert confirmed). Screener Premium confirmed as source (D-113). Monthly India importer built; first import 500/500 matched. Financial exclusion narrowed to banks/NBFCs/insurers (D-114, 419 investable) and REITs excluded (D-115). Screener has no 2-years-back profit → loss filter defined as last year + year before + trailing 12 months (D-116). Claude added the columns in Maaz's Screener via Chrome. Complete import: all required columns present; 37 of 419 investable show a loss in at least one of the three figures.
