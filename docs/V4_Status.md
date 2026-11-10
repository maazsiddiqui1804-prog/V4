# V4 Status

**Last updated:** 2026-11-10 · **Phase:** Build — all five phases have working code; waiting on Maaz items (Kite check, approvals, dashboard deploy) before go-live after the GMAT (D-130)

## Next session
1. **Waiting on Maaz (dashboard "Waiting on you"):**
   - T-059 ✅ decided 2026-11-10: Trading Engine = B2 (D-137). Engine, plan and config switched.
   - T-057 US Kite check: needs the "International" search in Kite (regular Kite didn't show it on 2026-11-10; US stocks are in beta at kite-beta.zerodha.com, accounts enabled in batches). Maaz expects it to appear soon.
   - T-060 ✅ dashboard online: https://investing-trading.streamlit.app/ (keep sharing set to "Only specific people").
   - T-054 approve US numbers · T-055 US weak-market rule · T-056 monthly vs quarterly US transfers · T-058 W-8BEN before first US buy · T-047 trading numbers.
2. **US module (phase 3):** code complete; cloud runs done: universe 334 → financials → shortlist of 40 (VRT, NTES, TSM, KARO, WB, NVDA, NOW, ANET, MSFT, META, GOOG, INTU, TTD, …; 7 non-USD reporters). Next: Kite check of the 40 (T-057) → Tiingo prices (confirmed only) → ranking. Foreign filers: size checked with price (drops small ones like KARO); P/E converted via FX + ADR ratio — Claude adds each confirmed name's ADR ratio to config/us_universe.yaml after checking the company's filing.
3. **Trading Engine (phase 4):** signals, costs, backtest, evening plan, watchlist, paper ledger (replays the backtest engine from the paper start date) built. Still to build after GMAT: Kite Connect data + daily login page (D-081: no stored password), daily evening job, midday checks (D-109), missed-check tripwire (D-049: needs a way for Maaz to confirm he checked).
4. **Phase 5:** Streamlit dashboard (dashboard/app.py, Action + Analysis) built and checked locally — deploy is T-060; quarterly report job (1 Jan/Apr/Jul/Oct); 12-month warning + 3-year kill test (shadow-portfolio vs index funds, after costs and tax); India tax estimates (rates to re-verify under Income-tax Act 2025); Monday check for silent jobs. Analysis view gains returns/risk/costs once real holdings exist.
5. After GMAT: December brief + sign-off (T-029) + first buys (T-030); Kite Connect; paper trading.

### T-059 — Trading strategy search (2026-11-10, SIMULATION, NOT LIVE) — details: research/2026-11-strategy-search/
Protocol fixed in advance: 15 years of today's Nifty 500 (Yahoo, split fixes), full costs; search on 2012–19 only (2,520 variants), 7 finalists declared, confirmed on 2020–22, then one untouched test on 2023–26 with pass rules written beforehand. Control: random entries with identical exits (removes survivorship drift).
| | 2012–19 | 2020–22 | 2023–26 (one-shot) | Edge over random entries (R) |
|---|---|---|---|---|
| **B2** 52-week-high breakout on 1.5× volume, top-20% 12-month strength, market above 200-day avg; stop 2×ATR; exit on close below 50-day avg (max 1 year) | 18%/yr, DD −16%, 0.51R | 22%, −15%, 0.49R | **21%, −17%, 0.51R, 566 trades** | +0.37 / +0.25 / +0.25 |
| **B1** = B2 without the market filter | 21%, −20%, 0.51R | 31%, −15%, 0.56R | 15%, −18%, 0.55R | +0.37 / +0.26 / +0.29 |
| **R4** top-10 by 6-month return, monthly, cash when market below 200-day | 25%, −29% | 16%, −39% | 27%, −30% | — |
| R1–R3 momentum rotation (no market filter) | 30–37%, −25 to −30% | 42–46%, ~−40% | 30–39%, −33 to −37% (failed drawdown rule) | — |
| C0 current V4 rules | 6%, 0.06R | 2%, 0.08R | **−3%, −0.03R (fail)** | |
| Survivor baseline (equal-weight all) / real Nifty 500 | 15% / 13% | 27% / 16% | 21% / 11% | |
Reading: every long strategy is flattered ~10 pts/yr by survivorship; breakout B-family holds a stable ~+0.25–0.37R edge over random entries in all three periods. What makes it work: let winners run (50-day-average trail, up to a year) — the 20-day time stop + 2R target in the current rules cut winners short. Holding ~1–2 months average, not 1–4 weeks.
**Decision: B2 adopted (D-137).** Realistic engine run of B2 (6 positions, ₹1L, highest strength first, ₹20 cr floor): 2012–19 13%/yr DD −31% 0.58R · 2020–22 30%/yr DD −27% 0.96R · 2023–26 13%/yr DD −15% 0.29R (just under the 0.3R bar). The research table above is per-trade and unconstrained, so it reads higher; the engine run is the one to expect. Roughly index-like returns with a per-trade edge; paper trading decides.

## Where we are
- Repo (private): github.com/maazsiddiqui1804-prog/v4. Claude GitHub App on this repo only. 169 automated checks pass.
- **Running automatically:** benchmark fund NAVs weekdays 22:47 IST; red-flag checks weekdays 10:47 / 13:17 / 15:23 IST (watchlist empty until the first list or holdings); monthly import whenever a file lands in data/inbox; monthly brief right after a successful import (guarded: none before 2026-12). Every job alerts Telegram on failure.
- **India data:** 500/500 Nifty 500 matched; 78 banks/NBFCs/insurers and 3 REITs excluded → 419 investable (D-113–D-115). Screener column list updated by Claude in Maaz's Chrome (profit years, cash-flow preceding year; 5 unused columns removed).
- **Benchmarks:** median of 21 AMFI index funds (D-121/D-122), history from 2025-09-15.
- **Holdings:** Console XLSX via inbox (D-119); account is V4-only (D-120) and empty.
- **Investment Engine (all 8 steps built, D-123–D-128):** kill filters → score (regime-aware) → India guardrail → buy plan → holding verdicts → red flags → monthly brief → frozen list. Dry run on 2026-11-09 data at ₹25k: BUY MCX 3 shares, IGIL 29 shares (preview only — nothing frozen, nothing sent).
- **US module (D-131–D-136):** SEC universe (334: 131 sized by float, 203 genuine foreign filers sized after Kite check); SEC financials (US-GAAP + IFRS, one reporting currency, renamed labels merged); kill filters + quality/growth shortlist; momentum + P/E-vs-growth guardrail; Nasdaq-100 fallback; combined caps (D-060/D-089); D-132 safeguards (LRS/TCS tracker, Schedule FA log, $45k estate warning, W-8BEN reminder); US section in the monthly brief (no US orders until approved). Monthly stages: fundamentals → shortlist → prices → rank (workflow "US data").
- **Trading Engine (D-040–D-049, rules per D-137):** signals, Zerodha delivery costs (zerodha.com/charges, 2026-11-10), backtest (gap fills, ATR stop, 50-day-average exit, market filter, drawdown brake — B2, D-137), evening plan + near-breakout watchlist. Workflow "Trading backtest" (manual). Starting numbers in config/placeholders.yaml → trading.
- **Cost guard:** health check runs Mondays and warns past 1,500 of 2,000 free Actions minutes (59 used by 2026-11-10).
- No numbers proven; all cut-offs are placeholders.

## Open items

| Item | When |
|---|---|
| Formal sign-off of starting numbers (T-029) and first buys (T-030) | December brief |
| Re-verify TCS ₹10L threshold under Income-tax Act 2025 (D-132) | Before first US transfer |
| Professional review of first ITR with US shares (Schedule FA) | ~mid-2027 |
| Confirm US universe limited to Zerodha-tradable list (D-022) | Phase 3 |
| Kite login page (Kite Connect) | Phase 4 |
| Trading placeholder numbers (now in config; backtest shows no edge — T-059) | Before paper trading (T-047) |
| US Kite check (International search not yet visible) | When Kite shows US stocks (T-057) |

## Build plan
- **Until GMAT (~28 Nov), D-130:** build phases 3–5 (US module, Trading Engine + backtest, dashboard); nothing goes live.
- **After GMAT (go-live):** December India brief + first buys; Kite Connect + daily login; paper trading starts (gate ≥3 months, D-048); US buying once the tax check is done (D-131).

## Fixed clocks after build
- Trading paper gate: ≥3 months + ≥30 trades + ≥0.3R avg net.
- Investment: 12-month warning review; 3-year kill test vs Nifty 500 and Nifty200 Quality 30 (index-fund median, D-121/D-122). Forward-tracking starts with the December 2026 list.
- Reviews: quarterly (Jan/Apr/Jul/Oct); annual strategy review in January.

## Session log
- **2026-10-24:** Brief absorbed. Build order, data, outputs, news-as-risk-filter decided.
- **2026-10-25:** Philosophy rethink, US/AI added, Kite Connect chosen, strategy for both engines, all flaw fixes, review calendar, build plan B. Docs created.
- **2026-11-08:** Build start moved to 2026-11-09 (D-086). Final open items closed (D-087–D-098). Amendments D-099–D-102, optimisation D-103–D-107, dashboard D-108, midday alerts D-109, GTT stops D-110. V4 Dashboard created and pinned (https://claude.ai/artifact/NP2ZkpE47Hp3F6FY7SAs1S).
- **2026-11-09 (long session, ~6 hrs by Maaz's choice, above D-087 pace):** Accounts, repo, Telegram alerts, cloud jobs. India data layer: Screener import (D-113–D-116), Project docs master (D-117), monthly inbox routine (D-118), holdings from Console XLSX (D-119/D-120), benchmarks from AMFI index funds (D-121/D-122). India Investment Engine fully built: kill filters (D-123), score (D-124), guardrail (D-125), buy plan (D-126), sell rules (D-127), red flags from NSE RSS (D-128), monthly brief + freeze; first real brief December (D-129). Bugs found and fixed along the way: workflow YAML, AMFI history columns, top-ups never triggering, rounding below ₹10k minimum, NSE feed cut off/malformed, duplicate feed items.
- **2026-11-09 (late):** Maaz chose to build all remaining phases before December and go live after the GMAT (D-130, option A: no daily logins or Kite Connect until then).
- **2026-11-09 (late):** D-085 beta condition dropped (US investing enabled on Maaz's account); US buys start after the tax check (D-131).
- **2026-11-09 (late, cont.):** US tax check done, go-ahead (D-132); US tradable rule (D-133) and AI universe rule by SEC industry codes (D-134) set after probing 30 names in the cloud.
- **2026-11-09/10 (late):** US universe builder (SEC float + industry codes, no Tiingo before Kite check, D-135); shortlist-first US ranking (D-136); SEC financials extractor; GitHub Actions outage blocked the final build run.
- **2026-11-10 (hygiene check):** every touchpoint aligned to D-137 and the app — repo docstrings/README/CLAUDE.md, one price source (prices branch), docs/ mirrors all 4 Project docs (manual gains a Touchpoints table + app step in session-end), US tax doc marked go-ahead/safeguards built, dashboard phases/milestones/open items/decisions (D-041/042/045 superseded) refreshed, app Build page synced via tools/sync_build.py. Waiting on Maaz: OK to delete the stale 4-year price copy on main (data/prices/).
- **2026-11-10 (later):** app address now investing-trading.streamlit.app; new Strategy & Philosophy page (why / rules live from config / scorecard vs target / diagnostics / review notes saved to data/app/review_notes.json). TODO before the December list: daily job to track each frozen list's forward returns by score part and guardrail (feeds the India Investing diagnostics).
- **2026-11-10 (afternoon, with Maaz):** strategy search → D-137 (B2 trading rules); app rebuilt as "Investing & Trading" (India Investing · India Trading · US Investing · Analysis · Build; amount box, tap-for-chart, filters, to-do ticks); daily app refresh job (weekdays 18:13 IST: prices kept on branch `prices`, watch-only B2 signals, job health); app link on every Telegram message. Build page = copy of the claude.ai dashboard tasks (data/app/build.json) — Claude refreshes it each session. Optional: GitHub key in Streamlit secrets to make to-do ticks stick.
- **2026-11-10 (unattended build, Maaz away, cont.):** paper ledger; Streamlit dashboard; reviews (D-064/D-065); quarterly report; tax estimates; silent-job check; US size check + currency-correct P/E; US shortlist of 40 built in the cloud.
- **2026-11-10 (unattended build, Maaz away):** US monthly pipeline + Actions-minutes guard; US universe built in the cloud (378 → 334 after excluding subsidiaries/preferreds); SEC financials fixed (label renames, currency mixing, missing debt); D-132 safeguards + combined caps + US brief section; Trading Engine signals, costs, backtest, evening plan; India price history for backtest (Yahoo, split fixes). First backtest: no edge (T-059). Kite "International" search not visible yet (T-057). No new decisions approved this session.
