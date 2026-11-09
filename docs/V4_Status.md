# V4 Status

**Last updated:** 2026-11-09 · **Phase:** Build — Setup + data layer (sprint week 1)

## Next session — sprint week 1, part 2
Pace until GMAT: 3–4 hrs/week (D-087).
1. Finish whatever account steps are still open (dashboard "Waiting on you" shows which).
2. Push repo skeleton to `v4` (drafted and tested 2026-11-09, waiting on GitHub username).
3. Telegram chat-ID helper + first health alert ("V4 is alive").
4. Screener importer, built on Maaz's first Nifty 500 export.

## Where we are
- Philosophy, strategy, asset mix, benchmarks, data sources, database, hosting: **finalised** (D-001 to D-112).
- Repo skeleton drafted and tested locally: rulebook (CLAUDE.md), shared database schema for both engines (13 tables), placeholder-numbers file, 4 passing checks. **Not pushed yet.**
- Accounts (GitHub, Kite Personal API app, Telegram bot, Secrets): Maaz walked through steps 2026-11-09; status per dashboard ticks.
- Nothing tested on real data. No numbers proven.

## Open items

| Item | When |
|---|---|
| US tax / estate tax / disclosure on GIFT City route (blocks US *buying* only, D-085) | Before first US buy |
| Confirm US universe limited to Zerodha-tradable list (D-022) | Build: US module |
| Placeholder numbers (filter cut-offs, valuation margins, liquidity floor, volume multiple, stretch limit, trail method) | Set during build as starting values; tested after |
| Kite login handoff for holdings sync: redirect URL is a placeholder (127.0.0.1); real handoff point to be designed (likely the Streamlit dashboard) | Build: holdings sync (T-018) |
| Repo docs/ vs Project docs: Project stays the authority; docs/ in repo is a copy refreshed at session end | Confirm with Maaz |

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
- **2026-11-09:** Build started. Database = SQLite in repo (D-111); dashboard hosting = Streamlit Community Cloud (D-112), both checked live. Account setup steps given (GitHub, Kite Personal API app, Telegram bot, Secrets). Repo skeleton + shared schema drafted and tested locally, waiting on GitHub username to push.
