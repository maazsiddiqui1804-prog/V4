# V4 Status

**Last updated:** 2026-11-10 · **Phase:** all five phases have working code; go-live after the GMAT (D-130). Older notes: docs/archive/V4_Status_history.md (repo only).

## Waiting on Maaz
| Task | What | When |
|---|---|---|
| T-057 | Kite check of the 40 US shortlisted names — waiting for Kite's US (International) search to appear on your account | When it appears |
| T-054 · T-055 · T-056 | Approve US numbers · US weak-market rule · monthly vs quarterly US transfers | Before first US buy |
| T-058 | Submit W-8BEN in Zerodha | Before first US buy |
| T-039 | Subscribe to Kite Connect (₹500/month) | After the GMAT |
| T-029 · T-030 | Sign off India starting numbers · first buys | December brief |
| T-047 | Sign off trading numbers (B2, D-137) | With paper results |

## Next (Claude)
1. When T-057 is done: mark Kite results, add each confirmed foreign name's ADR ratio (from its own filing), run US prices → ranking.
2. Kite switch-on after the GMAT (built and tested, currently off): set `kite_enabled: true` in config/app.yaml, `paper_start` in config/placeholders.yaml, uncomment the schedules in .github/workflows/kite_ops.yml, add kite_ops to the Monday silent-job check, confirm the ₹500 plan includes historical candles.
3. Keep jobs, app and dashboard running and aligned (D-138).

## Where we are
- **Repo:** github.com/maazsiddiqui1804-prog/v4 (private) · 200 automated checks pass · branches: `main`, `prices` (daily price history), `research-data` (15-year research prices).
- **App:** https://investing-trading.streamlit.app/ (private) — India Investing, India Trading (watch-only), US Investing, Analysis, Strategy & Philosophy, Build. Every Telegram message links it.
- **V4 Dashboard (claude.ai):** build tasks, rules, decisions, milestones; the app's Build page is a copy (tools/sync_build.py).
- **Scheduled jobs (all alert on failure; Monday check catches silent ones and Actions minutes):** benchmark NAVs weekdays 22:47 · red flags weekdays 10:47/13:17/15:23 · app refresh (prices, signals, job health) weekdays 18:13 · monthly import on inbox drop → monthly brief (none before Dec) · quarterly report 1 Jan/Apr/Jul/Oct · health check Mondays. Manual: US data stages, trading backtest, research prices.
- **India investing (D-113–D-129):** 419 investable of Nifty 500; filters → score → guardrail → buy plan → sells → red flags → brief. First real list December.
- **US investing (D-131–D-136):** universe 334 → 84 pass filters → shortlist 40 (7 non-USD reporters). Safeguards built (D-132). No US buys until approvals.
- **India trading (D-137 "B2"):** watch-only signals daily; paper after the GMAT; live only after D-048 (≥3 months, ≥30 trades, ≥0.3R). Capital 10% → up to 30% with live proof (D-100). Simulation 2023–26 (engine, 6 slots): ~13%/yr, worst fall −15%, 0.29R — not live.
- **Built, switched off until Kite Connect:** daily Kite login via the app (one tap; token encrypted, never stored in the repo), Kite as the price source, nightly paper-trading run with the D-048 gate line, missed-login tripwire (3 missed weekday logins → no new trades, D-049), login reminders 08:47/16:03, midday stop/trigger checks every ~30 min (D-109).
- **India list tracking (D-063):** every frozen list is followed vs the Nifty 500 from its freeze date; diagnostics on the Strategy page from December.
- All cut-offs are placeholders until evidence backs them.

## Open items
| Item | When |
|---|---|
| Re-verify TCS ₹10L threshold under Income-tax Act 2025 (D-132) | Before first US transfer |
| Professional review of first ITR with US shares (Schedule FA) | ~mid-2027 |

## Fixed clocks
- Trading paper gate: ≥3 months + ≥30 trades + ≥0.3R avg net (D-048).
- Investing: 12-month warning review; 3-year kill test vs Nifty 500 and Quality 30 index funds (D-064/D-065). Forward-tracking starts with the December 2026 list.
- Reviews: quarterly (Jan/Apr/Jul/Oct) = fixes; January = strategy (D-066).

## Last session (2026-11-10)
Strategy search → B2 trading rules (D-137); app rebuilt and renamed; daily app refresh; Telegram link; Strategy & Philosophy page; hygiene check across all touchpoints; clean-up (stale price copy and unused code removed, old notes archived).
