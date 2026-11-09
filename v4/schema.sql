-- V4 shared database (D-001: one database, both engines; D-111: SQLite in repo)
-- Dates are ISO text 'YYYY-MM-DD'. Money in INR unless a currency column says otherwise.

PRAGMA foreign_keys = ON;

-- Every stock or fund V4 knows about, India or US.
CREATE TABLE IF NOT EXISTS securities (
    security_id   INTEGER PRIMARY KEY,
    market        TEXT NOT NULL CHECK (market IN ('IN', 'US')),
    symbol        TEXT NOT NULL,              -- NSE symbol or US ticker
    name          TEXT,
    isin          TEXT,
    sector        TEXT,
    industry      TEXT,
    is_financial  INTEGER NOT NULL DEFAULT 0, -- bank/NBFC/insurer → excluded from investing (D-006, D-114)
    is_reit       INTEGER NOT NULL DEFAULT 0, -- REIT/InvIT → excluded from investing (D-115)
    currency      TEXT NOT NULL DEFAULT 'INR',
    added_on      TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE (market, symbol)
);

-- Which universe a stock belonged to on a date (Nifty 500, US AI value chain...).
CREATE TABLE IF NOT EXISTS universe_membership (
    security_id INTEGER NOT NULL REFERENCES securities(security_id),
    universe    TEXT NOT NULL,   -- 'NIFTY500', 'US_AI'
    as_of       TEXT NOT NULL,
    PRIMARY KEY (security_id, universe, as_of)
);

-- End-of-day prices for stocks (adjusted close where the source provides it).
CREATE TABLE IF NOT EXISTS prices (
    security_id INTEGER NOT NULL REFERENCES securities(security_id),
    date        TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL NOT NULL, adj_close REAL, volume REAL,
    source      TEXT NOT NULL,   -- 'screener', 'kite', 'tiingo', 'stooq'
    PRIMARY KEY (security_id, date)
);

-- Fundamentals: one row per stock, per metric, per snapshot. Long format so new metrics need no schema change.
CREATE TABLE IF NOT EXISTS fundamentals (
    security_id INTEGER NOT NULL REFERENCES securities(security_id),
    as_of       TEXT NOT NULL,   -- date of the export / filing pull
    metric      TEXT NOT NULL,   -- e.g. 'roce_5y_avg', 'debt_equity', 'pledge_pct', 'pe'
    value       REAL,
    period      TEXT,            -- e.g. 'FY2026', 'TTM'; NULL if not period-specific
    source      TEXT NOT NULL,
    PRIMARY KEY (security_id, as_of, metric, period)
);

-- Benchmark index levels (D-095, D-107): total-return series.
CREATE TABLE IF NOT EXISTS benchmark_levels (
    benchmark TEXT NOT NULL,     -- 'NIFTY500_TRI', 'NIFTY200_QUALITY30_TRI', 'NIFTY200_MOMENTUM30_TRI', 'NDX_TRI_INR'
    date      TEXT NOT NULL,
    level     REAL NOT NULL,
    source    TEXT NOT NULL,
    PRIMARY KEY (benchmark, date)
);

-- Benchmark index-fund NAVs from AMFI (D-121). Loaded monthly from data/benchmarks/navs.csv.
CREATE TABLE IF NOT EXISTS fund_navs (
    scheme_code TEXT NOT NULL,
    benchmark   TEXT NOT NULL,   -- 'nifty500', 'quality30', 'momentum30', 'nasdaq100'
    date        TEXT NOT NULL,
    nav         REAL NOT NULL,
    scheme_name TEXT,
    PRIMARY KEY (scheme_code, date)
);

CREATE TABLE IF NOT EXISTS fx_rates (
    pair  TEXT NOT NULL,         -- 'USDINR'
    date  TEXT NOT NULL,
    rate  REAL NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (pair, date)
);

-- Real holdings as synced from the broker (read-only sync).
CREATE TABLE IF NOT EXISTS holdings_snapshots (
    snapshot_date TEXT NOT NULL,
    security_id   INTEGER NOT NULL REFERENCES securities(security_id),
    engine        TEXT NOT NULL CHECK (engine IN ('investment', 'trading', 'outside_v4')),
    quantity      REAL NOT NULL,
    avg_price     REAL,
    PRIMARY KEY (snapshot_date, security_id, engine)
);

-- Investment Engine: each month's ranked list, frozen once published (D-063 forward-tracking).
CREATE TABLE IF NOT EXISTS investment_lists (
    list_month    TEXT NOT NULL,  -- 'YYYY-MM'
    security_id   INTEGER NOT NULL REFERENCES securities(security_id),
    rank          INTEGER NOT NULL,
    score_quality REAL, score_growth REAL, score_momentum REAL, score_total REAL,
    buy_below     REAL,           -- valuation guardrail price (D-025/D-101)
    passes_guardrail INTEGER,
    regime        TEXT,           -- 'normal' or 'weak' (D-103)
    frozen_at     TEXT,           -- set once published; frozen rows are never edited
    PRIMARY KEY (list_month, security_id)
);

-- Trading Engine: signals and the paper/live ledger (D-042..D-048).
CREATE TABLE IF NOT EXISTS trade_signals (
    signal_id    INTEGER PRIMARY KEY,
    signal_date  TEXT NOT NULL,
    security_id  INTEGER NOT NULL REFERENCES securities(security_id),
    entry_trigger REAL, stop REAL, target_2r REAL, quantity INTEGER,
    regime       TEXT,
    status       TEXT NOT NULL DEFAULT 'new'  -- new / skipped / taken / expired
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id     INTEGER PRIMARY KEY,
    signal_id    INTEGER REFERENCES trade_signals(signal_id),
    security_id  INTEGER NOT NULL REFERENCES securities(security_id),
    mode         TEXT NOT NULL CHECK (mode IN ('paper', 'live')),
    entry_date TEXT, entry_price REAL, quantity INTEGER,
    exit_date TEXT, exit_price REAL, exit_reason TEXT,
    costs REAL, tax REAL, r_multiple REAL
);

-- Overrides: any time Maaz departs from a signal, with reason; scored later (D-016).
CREATE TABLE IF NOT EXISTS overrides (
    override_id INTEGER PRIMARY KEY,
    date        TEXT NOT NULL,
    engine      TEXT NOT NULL,
    security_id INTEGER REFERENCES securities(security_id),
    signal      TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    reason      TEXT NOT NULL
);

-- Red-flag filings alarms (D-061).
CREATE TABLE IF NOT EXISTS red_flags (
    flag_id     INTEGER PRIMARY KEY,
    detected_at TEXT NOT NULL,
    security_id INTEGER NOT NULL REFERENCES securities(security_id),
    flag_type   TEXT NOT NULL,
    source_url  TEXT,
    reviewed    INTEGER NOT NULL DEFAULT 0
);

-- Every scheduled job run, success or failure. Silence must never mean "broken".
CREATE TABLE IF NOT EXISTS runs (
    run_id     INTEGER PRIMARY KEY,
    job        TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status     TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed', 'skipped')),
    message    TEXT
);
