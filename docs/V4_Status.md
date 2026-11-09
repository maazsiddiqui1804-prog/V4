# V4 Status

**Last updated:** 2026-11-10 · **Phase:** Build — all five phases have working code; waiting on Maaz items (Kite check, approvals, dashboard deploy) before go-live after the GMAT (D-130)

## Next session
1. **Waiting on Maaz (dashboard "Waiting on you"):**
   - T-059 **Trading backtest has no edge with starting numbers** — choose a path (options below).
   - T-057 US Kite check: needs the "International" search in Kite (regular Kite didn't show it on 2026-11-10; US stocks are in beta at kite-beta.zerodha.com, accounts enabled in batches). Maaz expects it to appear soon.
   - T-060 put the dashboard online on Streamlit (5 min, D-112).
   - T-054 approve US numbers · T-055 US weak-market rule · T-056 monthly vs quarterly US transfers · T-058 W-8BEN before first US buy · T-047 trading numbers.
2. **US module (phase 3):** code complete; cloud runs done: universe 334 → financials → shortlist of 40 (VRT, NTES, TSM, KARO, WB, NVDA, NOW, ANET, MSFT, META, GOOG, INTU, TTD, …; 7 non-USD reporters). Next: Kite check of the 40 (T-057) → Tiingo prices (confirmed only) → ranking. Foreign filers: size checked with price (drops small ones like KARO); P/E converted via FX + ADR ratio — Claude adds each confirmed name's ADR ratio to config/us_universe.yaml after checking the company's filing.
3. **Trading Engine (phase 4):** signals, costs, backtest, evening plan, watchlist, paper ledger (replays the backtest engine from the paper start date) built. Still to build after GMAT: Kite Connect data + daily login page (D-081: no stored password), daily evening job, midday checks (D-109), missed-check tripwire (D-049: needs a way for Maaz to confirm he checked).
4. **Phase 5:** Streamlit dashboard (dashboard/app.py, Action + Analysis) built and checked locally — deploy is T-060; quarterly report job (1 Jan/Apr/Jul/Oct); 12-month warning + 3-year kill test (shadow-portfolio vs index funds, after costs and tax); India tax estimates (rates to re-verify under Income-tax Act 2025); Monday check for silent jobs. Analysis view gains returns/risk/costs once real holdings exist.
5. After GMAT: December brief + sign-off (T-029) + first buys (T-030); Kite Connect; paper trading.

### T-059 — Trading backtest result (simulation, NOT live)
Nov 2022–Nov 2026, today's Nifty 500, Yahoo prices (7 missed splits/bonuses corrected), full Zerodha delivery costs + 0.1% slippage, ₹1L notional:
232 trades · avg **−0.11R** net · median −0.38R · win rate 39% · −17% total (−4.6%/yr) · worst drawdown −36% · D-048 bar (≥30 trades, ≥0.3R) **not met**.
Exits: stops avg −1.06R (incl. 5 overnight gaps avg −2.7R); time stop (20 days) avg +0.69R; only 7 trades reached 2R and trailed.
8 nearby variants (time stop 20/40, stop lookback 10/20, stretch 10%/5%): −0.11R to +0.06R overall; 2023–24 slightly positive, **2025–26 negative in every variant**. Results flatter reality (survivorship: today's index list).
Options (Claude's ranking):
- **A (recommended): keep rules, proceed to paper trading after GMAT as planned.** Paper is the real test; D-048 gate means no money at risk until ≥0.3R is proven. Cost: ~3 months of paper effort that may end in "no go".
- **B: before paper, Claude runs a pre-declared robustness study** (few variants fixed in advance, judged on 2025–26 as hold-out) and brings starting numbers for approval (T-047). Risk: curve-fitting if done loosely.
- **C: pause the Trading Engine** and put the 10% sleeve into the Investment Engine until the January strategy review (D-066) rethinks the setup.

## Where we are
- Repo (private): github.com/maazsiddiqui1804-prog/v4. Claude GitHub App on this repo only. 169 automated checks pass.
- **Running automatically:** benchmark fund NAVs weekdays 22:47 IST; red-flag checks weekdays 10:47 / 13:17 / 15:23 IST (watchlist empty until the first list or holdings); monthly import whenever a file lands in data/inbox; monthly brief right after a successful import (guarded: none before 2026-12). Every job alerts Telegram on failure.
- **India data:** 500/500 Nifty 500 matched; 78 banks/NBFCs/insurers and 3 REITs excluded → 419 investable (D-113–D-115). Screener column list updated by Claude in Maaz's Chrome (profit years, cash-flow preceding year; 5 unused columns removed).
- **Benchmarks:** median of 21 AMFI index funds (D-121/D-122), history from 2025-09-15.
- **Holdings:** Console XLSX via inbox (D-119); account is V4-only (D-120) and empty.
- **Investment Engine (all 8 steps built, D-123–D-128):** kill filters → score (regime-aware) → India guardrail → buy plan → holding verdicts → red flags → monthly brief → frozen list. Dry run on 2026-11-09 data at ₹25k: BUY MCX 3 shares, IGIL 29 shares (preview only — nothing frozen, nothing sent).
- **US module (D-131–D-136):** SEC universe (334: 131 sized by float, 203 genuine foreign filers sized after Kite check); SEC financials (US-GAAP + IFRS, one reporting currency, renamed labels merged); kill filters + quality/growth shortlist; momentum + P/E-vs-growth guardrail; Nasdaq-100 fallback; combined caps (D-060/D-089); D-132 safeguards (LRS/TCS tracker, Schedule FA log, $45k estate warning, W-8BEN reminder); US section in the monthly brief (no US orders until approved). Monthly stages: fundamentals → shortlist → prices → rank (workflow "US data").
- **Trading Engine (D-040–D-049):** signals, Zerodha delivery costs (zerodha.com/charges, 2026-11-10), backtest (gap fills, half at 2R, trail, 20-day time stop, drawdown brake), evening plan + near-breakout watchlist. Workflow "Trading backtest" (manual). Starting numbers in config/placeholders.yaml → trading.
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
- **2026-11-10 (unattended build, Maaz away, cont.):** paper ledger; Streamlit dashboard; reviews (D-064/D-065); quarterly report; tax estimates; silent-job check; US size check + currency-correct P/E; US shortlist of 40 built in the cloud.
- **2026-11-10 (unattended build, Maaz away):** US monthly pipeline + Actions-minutes guard; US universe built in the cloud (378 → 334 after excluding subsidiaries/preferreds); SEC financials fixed (label renames, currency mixing, missing debt); D-132 safeguards + combined caps + US brief section; Trading Engine signals, costs, backtest, evening plan; India price history for backtest (Yahoo, split fixes). First backtest: no edge (T-059). Kite "International" search not visible yet (T-057). No new decisions approved this session.
