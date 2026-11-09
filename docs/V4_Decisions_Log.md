# V4 Decisions Log

**Owner:** Maaz · **Maintained by:** Claude (V4 agent)
**Rule:** Only decisions Maaz explicitly approved go here. Proposals stay out until he says yes. Never delete an entry; supersede it with a new dated entry that names the one it replaces.
**Supersedes:** the original "V4 Philosophy & Strategy" doc (treated as a draft; this log is now the authority).

Status key: **APPROVED** = rule. **PLACEHOLDER** = approved structure, number to be set by testing and re-approved.

---

## 2026-10-24 — Foundations (from brief)

| ID | Decision | Status |
|---|---|---|
| D-001 | Build order: Investment Engine first, Trading Engine second (paper only). One shared database for both, designed for both from day one | APPROVED |
| D-002 | Home: Claude Code folder. CLAUDE.md = rulebook; docs/ = philosophy, decisions log, strategy, status. Scheduled runs are plain scripts on a cloud timer (GitHub Actions), not Claude sessions | APPROVED |
| D-003 | System never places orders. It sends instructions; Maaz executes | APPROVED |
| D-004 | Outputs pushed to phone (Telegram); dashboard as companion | APPROVED |
| D-005 | Data budget up to ₹1,000/month | APPROVED |
| D-006 | Banks, NBFCs, insurers excluded from India investing in v0.1 | APPROVED |

## 2026-10-25 — Philosophy

| ID | Decision | Status |
|---|---|---|
| D-010 | Purpose: beat index funds with low time spent, or switch V4 off | APPROVED |
| D-011 | Objective: beat benchmark by ≥2%/yr after costs and tax, rolling 5 years, with max drawdown no worse than the benchmark | APPROVED |
| D-012 | Horizon: V4 money not needed for 7+ years; MBA funded separately | APPROVED |
| D-013 | Time: 2–3 hrs/week once built; 8–10 hrs/week during build sprint | APPROVED |
| D-014 | Structure: two independent engines (Investment, Trading) on shared infrastructure | APPROVED |
| D-015 | Philosophy v2: (1) Invest in India + US companies with strong fundamentals for >3 years. (2) Trade Indian momentum breakouts, 1–4 week holds. (3) System screens, scores and signals; Maaz decides and executes | APPROVED |
| D-016 | Overrides: follow signals by default; any override needs a logged reason and is scored later vs the signal | APPROVED |
| D-017 | US purpose: AI exposure (Indian companies not yet AI-ready) | APPROVED |

## 2026-10-25 — Investment Engine

| ID | Decision | Status |
|---|---|---|
| D-020 | Markets: India + US, both in v0.1. US build gated: a US data source and tax picture must be confirmed first; if not ready by build date, India ships first | APPROVED |
| D-021 | India universe: Nifty 500 ex banks/NBFCs/insurers | APPROVED |
| D-022 | US universe: AI value chain (chips, cloud, software, data centres, power) by written industry/revenue rule, limited to stocks tradable on Zerodha. Changes are rule-only, logged; price performance never counts | APPROVED (tradable-list filter proposed 2026-10-25, confirm at US data session) |
| D-023 | Kill filters: losses in last 3 yrs; weak cash conversion; high debt/equity; low interest cover; high promoter pledge (India) | APPROVED / cut-offs PLACEHOLDER |
| D-024 | Score: Quality 60 (5–10 yr consistency of high return on capital + cash conversion; 3-yr window for AI universe) / Growth 40 (steady sales and profit growth) | APPROVED |
| D-025 | Valuation guardrail (not scored): buy below price where P/E hits own long-run typical level + margin (US margin wider); second check = P/E vs growth rate | APPROVED / margins PLACEHOLDER |
| D-026 | Output: monthly top 20 with "buy below" price + verdict on each holding | APPROVED |
| D-027 | Sell: thesis break (filter failure, red-flag filing, quality degradation) OR rank below top 100 for 2 consecutive months | APPROVED |
| D-028 | Portfolio: 15 India + 5–8 US holdings, equal weight; trim only above 2× target weight | APPROVED |
| D-029 | Idle money (nothing passes guardrail): cash / liquid fund | APPROVED |
| D-030 | AI/US exposure: hard cap, size set in asset-mix round | APPROVED / size OPEN |

## 2026-10-25 — Trading Engine

| ID | Decision | Status |
|---|---|---|
| D-040 | Universe: Nifty 500 + liquidity floor | APPROVED / floor PLACEHOLDER (~₹20 cr/day) |
| D-041 | Regime: when Nifty 500 below long-term (200-day) average, trades are half size | APPROVED (paper results must show weak-market trades are net positive, else becomes "no new trades") |
| D-042 | Setup: uptrend (50 > 200 DMA, price > 50 DMA) + top 20% relative strength + close at new 20-day high on high volume (~1.5× 20-day avg) + not overextended (distance above 20-day average) | APPROVED / numbers PLACEHOLDER |
| D-043 | Data: end-of-day. Signals ~6:30 PM; act next morning. Evening "near breakout" watchlist with trigger prices | APPROVED (alert vs GTT handling still to choose) |
| D-044 | Risk: 1% of trading capital per trade (0.5% in weak market); size = risk ÷ (entry − stop) | APPROVED (cut to 0.5% if gap losses exceed plan) |
| D-045 | Exits: stop below breakout; half off at 2R; trail the rest; ~20-trading-day time stop | APPROVED / trail method PLACEHOLDER |
| D-046 | Limits: max 6 open, max 3 per sector; no entries within 5 trading days of results; exclude surveillance-list stocks | APPROVED |
| D-047 | Paper first. Paper trades charged full costs, slippage, tax; stops filled at gap-open price | APPROVED |
| D-048 | Go-live gate: ≥3 months AND ≥30 trades AND avg net ≥0.3R/trade after costs | APPROVED |
| D-049 | Tripwire: 3+ missed daily checks → no new trades until resumed. Engine keeps running during ISB | APPROVED |

## 2026-10-25 — System-wide

| ID | Decision | Status |
|---|---|---|
| D-060 | Combined cap across both engines: max 10% of V4 per stock, 25% per sector; trading signals that would breach are skipped | APPROVED |
| D-061 | News: official filings only, as a risk alarm, never a buy signal. Investment red flags (auditor exit, rating downgrade, pledge rise, CEO/CFO exit, regulatory order; US: auditor change, restatement, exec departure, downgrade) freeze buying + trigger review | APPROVED |
| D-062 | Benchmarks: India vs Nifty 500 ex-financials-style index + quality index fund; US vs its own index in INR; total vs blend | APPROVED / exact names OPEN |
| D-063 | Validation: forward-track — freeze each month's list, score at 1 and 3 years | APPROVED |
| D-064 | Kill test: at 3 years, India sleeve must beat its benchmark AND a quality index fund after costs and tax, else switch | APPROVED |
| D-065 | 12-month warning review: if lagging both, deep review; no automatic switch | APPROVED |
| D-066 | Reviews: quarterly (Jan/Apr/Jul/Oct) = fixes only (bugs, data, costs, breaches); trading numbers change only with ≥30 new trades of evidence. Strategy rules change only at annual review (January). No rule changes mid-slump | APPROVED |
| D-067 | Quarterly report: performance vs benchmarks, breaches, overrides scorecard, ranked proposed fixes (approve/reject) | APPROVED |

## 2026-10-25 — Infrastructure and build

| ID | Decision | Status |
|---|---|---|
| D-080 | Prices: Kite Connect paid (₹500/month, verified 2026-10-25) for prices + history. Holdings: Kite API | APPROVED |
| D-081 | Daily Kite login: one tap after 6 AM (token expires 6 AM next day); Telegram reminder ~8–9 AM, nudge ~4 PM; missed login = run skipped, re-run available. Never automate login with stored password/2FA | APPROVED |
| D-082 | India fundamentals: monthly Screener export | APPROVED |
| D-083 | Runs in the cloud (GitHub Actions); laptop can be off. Dashboard private, phone-accessible | APPROVED / hosting OPEN |
| D-084 | Build plan B: full system in ~4–5 week sprint, 8–10 hrs/week, from ~1 Dec 2026 (mid-Jan if GMAT retake). Pre-build design hour weekly until GMAT | APPROVED |
| D-085 | US stock buying waits for Zerodha beta to end + tax check | APPROVED |

## 2026-11-08 — Build timing

| ID | Decision | Status |
|---|---|---|
| D-086 | **Supersedes D-084 start date.** Finalise open items and start building on 2026-11-09, before the GMAT (Maaz accepted the trade-off with GMAT prep time). Build order and one-engine-at-a-time rule unchanged. Weekly pace to confirm at session start | APPROVED |

## 2026-11-08 — Final open items

| ID | Decision | Status |
|---|---|---|
| D-087 | Pace: 3–4 hrs/week until GMAT (setup + data layer); full 8–10 hrs/week sprint resumes after GMAT | APPROVED |
| D-088 | Engine split: 90% investment / 10% trading | APPROVED |
| D-089 | AI/US cap = max 30% of the investment sleeve (sets size for D-030) | APPROVED |
| D-090 | No gold sleeve | APPROVED |
| D-091 | Capital: no lump sum into V4 now. Investment Engine goes live with real money from day one via monthly additions of ₹25–50k; existing investments stay in Maaz's current setup outside V4. Any future lump sum is deployed in thirds over 3 monthly runs | APPROVED |
| D-092 | Monthly additions buy current top-ranked names passing the guardrail, or fill underweight holdings | APPROVED |
| D-093 | **Supersedes cost scope of D-011.** V4 is judged after trading costs (brokerage, forex markup, slippage, tax). Data subscriptions are excluded from the comparison | APPROVED |
| D-094 | Data budget stays up to ₹1,000/month (Kite ₹500; US data free) | APPROVED |
| D-095 | **Supersedes benchmark names in D-062/D-064.** India = Nifty 500 TRI (no official ex-financials index found 2026-11-08), dashboard shows the lag caused by excluding financials. Quality bar = Nifty200 Quality 30 TRI. US = Nasdaq-100 TRI in INR | APPROVED |
| D-096 | US data: SEC EDGAR (free fundamentals, standardised by V4) + Tiingo free tier (adjusted end-of-day prices); Stooq free CSVs as price backup. Checked live 2026-11-08 | APPROVED |
| D-097 | Near-breakout watchlist handled with Kite price alerts (resolves D-043 open item) | APPROVED |
| D-098 | Paper trading notional capital: ₹1L | APPROVED |

## 2026-11-08 — Strategy amendments (more aggressive)

| ID | Decision | Status |
|---|---|---|
| D-099 | **Supersedes D-024 weights.** Investment score = Quality + Growth + Price momentum (starting weights 40 / 30 / 30). Kill filters unchanged | APPROVED / weights + momentum lookback PLACEHOLDER |
| D-100 | **Supersedes fixed split in D-088.** Trading earns capital in stages: 10% at go-live → 20% after 50 live trades at ≥0.3R avg net → max 30% after 100 live trades; steps back down if results fade | APPROVED / step-down rule PLACEHOLDER |
| D-101 | **Supersedes D-025 for US only.** US guardrail = P/E vs growth only; own-history P/E check dropped for US. India guardrail unchanged | APPROVED / threshold PLACEHOLDER |
| D-102 | US fallback: if no US stock passes the guardrail for 3 consecutive months, US-sleeve money goes to a Nasdaq-100 index fund; switch back to picks when names pass | APPROVED |

## 2026-11-08 — Optimisation (crash guards, small-capital fixes)

| ID | Decision | Status |
|---|---|---|
| D-103 | Regime-aware momentum: when Nifty 500 is below its 200-day average, investment weights shift from 40/30/30 to 55/30/15 (Quality/Growth/Momentum) | APPROVED / weights PLACEHOLDER |
| D-104 | Trading drawdown brake: if trading sleeve falls >15% from its peak, no new trades until the next quarterly review | APPROVED / 15% PLACEHOLDER |
| D-105 | Minimum buy per stock: ₹10k. Monthly additions buy 2–5 names; portfolio fills over time | APPROVED |
| D-106 | **Supersedes D-080 start timing.** Kite Connect (₹500/mo) and the daily login start only when the Trading Engine is built. Until then: Screener export supplies India prices/P-E; holdings via free Kite Personal API (login only on run days) | APPROVED |
| D-107 | Diagnostic benchmark: Nifty200 Momentum 30 TRI shown on dashboard/reports. Not part of the kill test | APPROVED |

## 2026-11-08 — Dashboard

| ID | Decision | Status |
|---|---|---|
| D-108 | Dashboard has two views. **Action** (default): trades = entry, stop-loss, target, quantity, stop moves, exits; investments = amount, buy-below price, sell signals. **No stop-loss or target on investments.** **Analysis**: charts and tables covering portfolio, returns, risk, tax obligations, costs, trade journal, overrides, history. Tax figures are estimates using rules verified live at build, not tax advice | APPROVED |

## 2026-11-08 — Midday alerts and stop protection

| ID | Decision | Status |
|---|---|---|
| D-109 | Midday alerts: red-flag filings checked ~3× during market hours from day one. Once Kite Connect starts (Trading Engine), a scheduled price check every ~30 min in market hours alerts on stop hit, target hit, or watchlist trigger crossed. Entry rules unchanged (close-based signals; watchlist via Kite alerts per D-097) | APPROVED / frequency subject to cloud-schedule limits, verify at build |
| D-110 | When trading goes live, Maaz places each stop-loss as a GTT order in Kite at entry, so stops execute even if he misses an alert. System never places orders (D-003 unchanged) | APPROVED |

## 2026-11-09 — Infrastructure choices

| ID | Decision | Status |
|---|---|---|
| D-111 | **Resolves database choice (D-001, D-083).** Database = one SQLite file inside the private GitHub repo; every scheduled run commits it (built-in history/audit trail). Revisit if repo size grows once Trading Engine adds daily prices (fix: move prices to compressed files) | APPROVED |
| D-112 | **Resolves hosting OPEN in D-083.** Private dashboard hosted on Streamlit Community Cloud (one private app, Google/email login, phone-accessible, free; checked live 2026-11-09). Built in phase 5 | APPROVED |

## 2026-11-09 — India data source and universe

| ID | Decision | Status |
|---|---|---|
| D-113 | **Confirms D-082 source.** Monthly India fundamentals come from Maaz's existing Screener Premium subscription (export is Premium-only, checked live 2026-11-09). No new cost to V4. Universe membership comes from NSE's official Nifty 500 CSV; Screener rows are matched to it by ISIN | APPROVED |
| D-114 | **Clarifies D-006/D-021.** Investment exclusion = banks, NBFCs and insurers only, identified by Screener industry group Banks / Finance / Insurance (78 of NSE's 98 "Financial Services" names on 2026-11-09). Exchanges, AMCs, depositories, brokers and fintech stay investable. An NSE financial that can't be matched to Screener is excluded cautiously | APPROVED |
| D-115 | REITs (NSE series RR) excluded from the Investment Engine; filters are built for operating companies | APPROVED |
| D-116 | **Defines D-023 "losses in last 3 years" for India.** Screener has no "net profit 2 years back" (checked 2026-11-09, incl. custom ratios), so the loss filter rejects a company with a loss in the last full year, the year before, or the trailing 12 months. A loss 3 years ago is not caught directly; the 5–10 yr ROCE quality score still penalises erratic histories | APPROVED |

## 2026-11-09 — Docs

| ID | Decision | Status |
|---|---|---|
| D-117 | Project docs (claude.ai) are the master copy of the decisions log and status note. The repo's docs/ folder is a copy Claude refreshes at the end of each session | APPROVED |

## 2026-11-09 — Monthly routine, holdings, benchmarks

| ID | Decision | Status |
|---|---|---|
| D-118 | Monthly India data routine: Maaz drops the Screener export into `data/inbox/` on github.com; a cloud job fetches NSE's Nifty 500 list itself (fallbacks: a list in the inbox, else the last archived one, with a warning), imports, archives raw files by date, and sends a Telegram report. Works with laptop off and no Claude session (D-002, D-083). Backup: Claude imports from chat | APPROVED |
| D-119 | **Supersedes holdings source in D-106.** Until the Trading Engine (Kite Connect) is built, holdings come from the Zerodha Console holdings XLSX dropped into the inbox once a month. Importer is built when the first V4 buys produce a real file. Paid Kite Connect timing in D-106 unchanged | APPROVED |
| D-120 | Maaz's Zerodha account holds only V4 positions; his other portfolio sits in a separate family account outside V4 (consistent with D-091). Investment vs trading positions in the same account are told apart by V4's own trade records (Trading Engine build) | APPROVED |
| D-121 | **Supersedes data source in D-095 (benchmark targets unchanged).** Benchmarks come from index-fund NAVs in AMFI's official daily NAV file (investable, after fund costs, in INR), not raw TRIs. Exact TRIs are only reachable via an undocumented feed behind bot detection (checked 2026-11-09). Recorded every weekday ~22:47 IST to data/benchmarks/navs.csv | APPROVED |
| D-122 | Each benchmark = chained median daily return of all qualifying Direct-Growth index funds: Nifty 500 (6 funds), Nifty200 Quality 30 (5), Nifty200 Momentum 30 (8, pure index funds only), Nasdaq-100 INR (2 clearly labelled Direct-Growth funds; others unlabelled in AMFI file). Scheme codes in config/benchmarks.yaml | APPROVED |

## 2026-11-09 — India Investment Engine: filters, score, guardrail

| ID | Decision | Status |
|---|---|---|
| D-123 | **Sets D-023 starting cut-offs ("Balanced").** Debt-to-equity ≤ 1.5; interest cover ≥ 3× (not checked when D/E < 0.1); promoter pledge ≤ 10%; cash conversion ≥ 0.7 measured over 2 years ((CFO last + preceding) ÷ (net profit last + preceding)). A blank number = fail. On 2026-11-09 data: 254 of 419 pass | APPROVED / numbers PLACEHOLDER |
| D-124 | **Score method under D-099/D-103.** Each input ranked 0–100 among filter survivors (missing = bottom). Quality = lowest of 3/5/10-yr average ROCE (needs ≥2 periods) + 2-yr cash conversion, equal parts. Growth = lower of 3/5-yr sales growth and lower of 3/5-yr profit growth, equal parts. Momentum = average rank of 6- and 12-month returns. Weak-market signal = Nifty 500 benchmark line (D-122) vs its 200-day average, history backfilled from AMFI; if unavailable, the cautious 55/30/15 weights are used | APPROVED / momentum lookback PLACEHOLDER |
| D-125 | **Sets D-025 India starting values ("Balanced").** Buy-below = price × (10-yr P/E × 1.2) ÷ current P/E (5-yr P/E if 10-yr blank); second check PEG ≤ 2.0; blank or negative PEG fails. On 2026-11-09 data: 8 of top 20 buyable | APPROVED / numbers PLACEHOLDER |
