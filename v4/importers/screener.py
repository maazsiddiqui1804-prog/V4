"""Monthly India import (D-082): official Nifty 500 list + Screener export → database.

Plain English:
1. The NSE file decides WHICH stocks are in the universe (D-021).
   Banks, NBFCs and insurers are flagged so the Investment Engine skips them
   (D-006, D-114): Screener industry group Banks / Finance / Insurance.
   Exchanges, fund houses, depositories, brokers and fintech stay in.
   REITs (NSE series RR) are flagged and skipped too (D-115).
   NSE's 'DUMMY' placeholder rows are ignored.
2. The Screener file supplies the NUMBERS. Rows are matched by ISIN, the
   permanent ID code every listed share has.
3. Every numeric Screener column is stored under a tidy name, so adding a
   column in Screener later needs no code change.
4. A report says what matched, what's missing, and which needed columns are absent.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from v4.db import connect, init_db, DB_PATH

# Columns the strategy needs (decision IDs in brackets). The import still runs
# without them, but the report lists them so Maaz can add them in Screener.
REQUIRED = {
    "current_price": "basics",
    "market_capitalization": "basics",
    "price_to_earning": "valuation guardrail (D-025)",
    "debt_to_equity": "kill filter (D-023)",
    "interest_coverage_ratio": "kill filter (D-023)",
    "pledged_percentage": "kill filter (D-023)",
    "cash_from_operations_last_year": "cash conversion (D-023)",
    "average_return_on_capital_employed_3years": "quality (D-024)",
    "sales_growth_3years": "growth (D-099)",
    "sales_growth_5years": "growth (D-099)",
    "profit_growth_3years": "growth (D-099)",
    "profit_growth_5years": "growth (D-099)",
    "return_over_6months": "momentum (D-099)",
    "return_over_1year": "momentum (D-099)",
    "peg_ratio": "valuation second check (D-025)",
}
# Needed but matched loosely, because Screener's exact names vary.
REQUIRED_PATTERNS = {
    # D-023 needs three separate annual profit figures, so each year is checked on its own.
    r"^(net_profit|profit_after_tax)_last_year$": "losses in last 3 years (D-023): latest year",
    r"^(net_profit|profit_after_tax)_preceding_year$": "losses in last 3 years (D-023): year before",
    r"^(net_profit|profit_after_tax)_(2|3)_?years?_back$": "losses in last 3 years (D-023): 2 years back",
    r"^average_return_on_capital_employed_(5|10)years$": "5–10 year quality consistency (D-024)",
    r"^historical_pe_(5|10)years$": "own long-run P/E for India guardrail (D-025)",
}

# D-114: which Screener industry groups count as banks / NBFCs / insurers.
EXCLUDED_FINANCIAL_GROUPS = {"Banks", "Finance", "Insurance"}

ID_COLUMNS = {"Name", "BSE Code", "NSE Code", "ISIN Code", "Industry Group", "Industry"}


def slug(col: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", col.strip()).strip("_").lower()
    return s


@dataclass
class Report:
    as_of: str
    universe: int = 0
    financials: int = 0
    financials_kept: int = 0
    reits: int = 0
    matched: int = 0
    unmatched: list = field(default_factory=list)
    missing_required: dict = field(default_factory=dict)
    blank_values: dict = field(default_factory=dict)

    def text(self) -> str:
        investable = self.universe - self.financials - self.reits
        lines = [
            f"Import as of {self.as_of}",
            f"Nifty 500 members: {self.universe} (banks/NBFCs/insurers excluded: {self.financials}, other financials kept: {self.financials_kept}, REITs excluded: {self.reits}, left for investing: {investable})",
            f"Matched to Screener: {self.matched}/{self.universe}",
        ]
        if self.unmatched:
            lines.append("Not found in Screener: " + ", ".join(self.unmatched))
        if self.missing_required:
            lines.append("Needed columns missing from the Screener export:")
            lines += [f"  - {k}: {v}" for k, v in self.missing_required.items()]
        if self.blank_values:
            lines.append("Blank values among matched stocks (column: count):")
            lines += [f"  - {k}: {v}" for k, v in self.blank_values.items() if v]
        return "\n".join(lines)


def load_nifty_list(path: Path) -> pd.DataFrame:
    n = pd.read_csv(path).dropna(subset=["Symbol"])
    n = n[~n["ISIN Code"].astype(str).str.upper().str.startswith("DUM")]
    n = n[~n["Symbol"].astype(str).str.upper().str.startswith("DUMMY")]
    return n


def import_month(nifty_csv: Path, screener_csv: Path, as_of: str, db_path: Path = DB_PATH) -> Report:
    init_db(db_path)
    nifty = load_nifty_list(nifty_csv)
    scr = pd.read_csv(screener_csv)
    scr.columns = [c.strip() for c in scr.columns]
    numeric_cols = [c for c in scr.columns if c not in ID_COLUMNS]
    slugs = {c: slug(c) for c in numeric_cols}

    rep = Report(as_of=as_of, universe=len(nifty))
    have = set(slugs.values())
    rep.missing_required = {k: v for k, v in REQUIRED.items() if k not in have}
    for pat, why in REQUIRED_PATTERNS.items():
        if not any(re.search(pat, s) for s in have):
            rep.missing_required[pat.strip("^$")] = why

    merged = nifty.merge(scr, on="ISIN Code", how="left", suffixes=("_nse", ""), indicator=True)
    rep.unmatched = merged.loc[merged["_merge"] == "left_only", "Symbol"].tolist()
    nse_fin = merged["Industry_nse"] == "Financial Services"
    group = merged["Industry Group"] if "Industry Group" in merged else pd.Series(None, index=merged.index)
    # Matched → use Screener's group. Unmatched → cautious: treat any NSE financial as excluded.
    merged["is_fin"] = nse_fin & (group.isin(EXCLUDED_FINANCIAL_GROUPS) | (merged["_merge"] == "left_only"))
    merged["is_reit"] = merged["Series"] == "RR"
    rep.financials = int(merged["is_fin"].sum())
    rep.financials_kept = int((nse_fin & ~merged["is_fin"]).sum())
    rep.reits = int(merged["is_reit"].sum())
    ok = merged[merged["_merge"] == "both"]
    rep.matched = len(ok)
    rep.blank_values = {slugs[c]: int(ok[c].isna().sum()) for c in numeric_cols
                        if slugs[c] in REQUIRED and ok[c].isna().any()}

    with connect(db_path) as conn:
        for _, r in merged.iterrows():
            conn.execute(
                """INSERT INTO securities (market, symbol, name, isin, sector, industry, is_financial, is_reit)
                   VALUES ('IN', ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(market, symbol) DO UPDATE SET
                     name=excluded.name, isin=excluded.isin, sector=excluded.sector,
                     industry=excluded.industry, is_financial=excluded.is_financial,
                     is_reit=excluded.is_reit""",
                (r["Symbol"], r["Company Name"], r["ISIN Code"], r["Industry_nse"],
                 r["Industry"] if r["_merge"] == "both" else None,
                 int(r["is_fin"]), int(r["is_reit"])),
            )
        ids = dict(conn.execute("SELECT symbol, security_id FROM securities WHERE market='IN'").fetchall())
        conn.executemany(
            "INSERT OR IGNORE INTO universe_membership VALUES (?, 'NIFTY500', ?)",
            [(ids[s], as_of) for s in nifty["Symbol"]],
        )
        rows = []
        for _, r in ok.iterrows():
            sid = ids[r["Symbol"]]
            for c in numeric_cols:
                v = pd.to_numeric(r[c], errors="coerce")
                if pd.notna(v):
                    rows.append((sid, as_of, slugs[c], float(v), None, "screener"))
        # Re-importing the same month replaces that month's numbers, nothing else.
        conn.execute("DELETE FROM fundamentals WHERE as_of=? AND source='screener'", (as_of,))
        conn.executemany("INSERT INTO fundamentals VALUES (?,?,?,?,?,?)", rows)
        conn.executemany(
            "INSERT OR REPLACE INTO prices (security_id, date, close, source) VALUES (?, ?, ?, 'screener')",
            [(ids[r["Symbol"]], as_of, float(r["Current Price"])) for _, r in ok.iterrows()
             if pd.notna(r.get("Current Price"))],
        )
    return rep


if __name__ == "__main__":
    nifty_csv, screener_csv, as_of = sys.argv[1], sys.argv[2], sys.argv[3]
    print(import_month(Path(nifty_csv), Path(screener_csv), as_of).text())
