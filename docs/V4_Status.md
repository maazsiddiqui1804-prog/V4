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
1. Before the December list: track each frozen list's forward returns by score part and by guardrail (feeds the app's India diagnostics).
2. When T-057 is done: mark Kite results, add each confirmed foreign name's ADR ratio (from its own filing), run US prices → ranking.
3. After the GMAT: Kite Connect data + daily login page (no stored password, D-081), daily evening paper run, midday checks (D-109), missed-check tripwire (D-049).

## Where we are
- **Repo:** github.com/maazsiddiqui1804-prog/v4 (private) · 183 automated checks pass · branches: `main`, `prices` (daily price history), `research-data` (15-year research prices).
- **App:** https://investing-trading.streamlit.app/ (private) — India Investing, India Trading (watch-only), US Investing, Analysis, Strategy & Philosophy, Build. Every Telegram message links it.
- **V4 Dashboard (claude.ai):** build tasks, rules, decisions, milestones; the app's Build page is a copy (tools/sync_build.py).
- **Scheduled jobs (all alert on failure; Monday check catches silent ones and Actions minutes):** benchmark NAVs weekdays 22:47 · red flags weekdays 10:47/13:17/15:23 · app refresh (prices, signals, job health) weekdays 18:13 · monthly import on inbox drop → monthly brief (none before Dec) · quarterly report 1 Jan/Apr/Jul/Oct · health check Mondays. Manual: US data stages, trading backtest, research prices.
- **India investing (D-113–D-129):** 419 investable of Nifty 500; filters → score → guardrail → buy plan → sells → red flags → brief. First real list December.
- **US investing (D-131–D-136):** universe 334 → 84 pass filters → shortlist 40 (7 non-USD reporters). Safeguards built (D-132). No US buys until approvals.
- **India trading (D-137 "B2"):** watch-only signals daily; paper after the GMAT; live only after D-048 (≥3 months, ≥30 trades, ≥0.3R). Capital 10% → up to 30% with live proof (D-100). Simulation 2023–26 (engine, 6 slots): ~13%/yr, worst fall −15%, 0.29R — not live.
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
