# V4 Status

**Last updated:** 2026-11-09 · **Phase:** Build — India Investment Engine code complete; building phases 3–5 before December (D-130)

## Next session
1. ✅ US tax check done, go-ahead given (D-132; Project doc V4_US_Tax_Check.md).
2. **Phase 3: US AI module** (D-130): ✅ tradable rule (D-133) and universe rule (D-134) set; SEC access working (contact email in Secret SEC_CONTACT_EMAIL). Universe builder done (SEC-only, D-135; float read for all quarters after a fix); first full build blocked by a GitHub Actions outage (2026-11-09 18:12 UTC) — rerun when resolved. Next: SEC financials (extractor built, probe pending), US score on quality+growth → top ~40 shortlist (D-136) → Kite check via Chrome → Tiingo for confirmed names only, Tiingo prices (Stooq backup; Tiingo key → Maaz adds to GitHub Secrets), AI value-chain universe rule, US guardrail (P/E vs growth, D-101), Nasdaq-100 fallback (D-102), combined caps (D-060, D-089).
3. Then Phase 4: Trading Engine + backtest (no daily login, no Kite Connect until after GMAT), then Phase 5: dashboard.
4. After GMAT: December brief + sign-off (T-029) + first buys (T-030); subscribe Kite Connect; start paper trading.
5. Known gaps for first quarterly review: short histories for recent listings; red-flag name matching.

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
| Re-verify TCS ₹10L threshold under Income-tax Act 2025 (D-132) | Before first US transfer |
| Professional review of first ITR with US shares (Schedule FA) | ~mid-2027 |
| Confirm US universe limited to Zerodha-tradable list (D-022) | Phase 3 |
| Kite login page (Kite Connect) | Phase 4 |
| Trading placeholder numbers (liquidity floor, volume multiple, stretch limit, trail method) | Phase 4 (T-047) |

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
