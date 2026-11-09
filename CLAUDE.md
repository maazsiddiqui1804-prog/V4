# V4 — Rulebook for Claude

V4 is Maaz's personal rules-based system: India + US long-term investing (Investment Engine) and India momentum trading (Trading Engine, paper first). Maaz is not a programmer. Claude writes and maintains the code; Maaz decides.

## Authority
- `docs/V4_Decisions_Log.md` — every approved rule. If code and log disagree, the log wins; fix the code or ask.
- `docs/V4_Status.md` — where the build is and what's next.
- Read both before changing anything.

## Hard limits (never break, even if asked)
1. **No orders.** Code never places, modifies or cancels an order. Only read-only broker calls (holdings, positions, quotes, history). (D-003)
2. **No secrets in the repo.** Keys live only in GitHub Secrets, entered by Maaz. Read them from environment variables. Never log them.
3. **Never automate the Kite login** with a stored password or 2FA secret. (D-081)
4. Never present backtested or paper results as live.
5. No rule changes outside the review calendar (quarterly = fixes, January = strategy), except emergency fixes for broken systems. (D-066)

## Build rules
- One engine half-built at a time. Order: data layer → India Investment → US module → Trading (paper) → dashboard/reviews.
- Investment and Trading Engines share data and infrastructure only; separate rules, portfolios, outputs. (D-014)
- Small, explained changes. After each change report: what changed, what was tested, what's unverified, next step — in plain English.
- Every scheduled job alerts Telegram on failure. Silence must never mean "broken".
- Untested numbers live in `config/placeholders.yaml`, marked PLACEHOLDER, never hard-coded.

## Layout
```
v4/
  CLAUDE.md            this rulebook
  docs/                decisions log, status (mirrors of the claude.ai Project docs)
  config/              settings and placeholder numbers (no secrets)
  data/v4.sqlite       the one shared database (D-001, D-111)
  data/raw/            raw imports (Screener exports etc.)
  v4/                  Python package: db, importers, engines, alerts
  tests/               automated checks
  .github/workflows/   scheduled cloud runs (D-002, D-083)
```
