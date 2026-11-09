"""Holdings from the Zerodha Console holdings XLSX (D-119, D-120).

Plain English:
- Console's file has a summary block on top, then a table that starts at a
  row reading "Symbol | ISIN | ...". This finds that row on each sheet.
- Reads the Equity and Mutual Funds sheets (Combined repeats them, so it's skipped).
- Quantity held = available + discrepant + pledged (margin) + pledged (loan).
  Any pledged or discrepant shares are flagged: V4 holdings shouldn't have either.
- Matches holdings by ISIN; anything not already known (e.g. an ETF or a liquid
  fund) is added as a new security.
- The account is V4-only (D-120). Until the Trading Engine keeps its own trade
  records, every holding is tagged 'investment'.
- The raw file is never archived: it contains the client ID.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import openpyxl

from v4.db import connect, init_db, DB_PATH

SHEETS = ("Equity", "Mutual Funds")
QTY_COLS = ("Quantity Available", "Quantity Discrepant",
            "Quantity Pledged (Margin)", "Quantity Pledged (Loan)")


@dataclass
class HoldingsReport:
    as_of: str
    positions: int = 0
    warnings: list = field(default_factory=list)

    def text(self) -> str:
        lines = [f"Holdings as of {self.as_of}: {self.positions} positions imported"]
        lines += [f"⚠️ {w}" for w in self.warnings]
        return "\n".join(lines)


def is_holdings_file(path: Path) -> bool:
    if path.suffix.lower() != ".xlsx":
        return False
    try:
        wb = openpyxl.load_workbook(path, read_only=True)
        return "Equity" in wb.sheetnames and "Combined" in wb.sheetnames
    except Exception:
        return False


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def read_rows(path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(path, data_only=True)
    out = []
    for name in SHEETS:
        if name not in wb.sheetnames:
            continue
        rows = list(wb[name].iter_rows(values_only=True))
        header_idx = next((i for i, r in enumerate(rows)
                           if r and "Symbol" in r and "ISIN" in r), None)
        if header_idx is None:
            continue
        header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        for r in rows[header_idx + 1:]:
            rec = dict(zip(header, r))
            sym, isin = rec.get("Symbol"), rec.get("ISIN")
            if not sym or not isin:
                continue
            rec["sheet"] = name
            out.append(rec)
    return out


def import_holdings(path: Path, as_of: str | None = None, db_path: Path = DB_PATH) -> HoldingsReport:
    as_of = as_of or date.today().isoformat()
    init_db(db_path)
    rep = HoldingsReport(as_of=as_of)
    rows = read_rows(path)
    with connect(db_path) as c:
        c.execute("DELETE FROM holdings_snapshots WHERE snapshot_date=?", (as_of,))
        for r in rows:
            isin = str(r["ISIN"]).strip()
            sym = re.sub(r"-[A-Z]$", "", str(r["Symbol"]).strip())   # Console adds e.g. '-E'
            qty = sum(_num(r.get(k)) for k in QTY_COLS)
            if qty <= 0:
                continue
            pledged = _num(r.get("Quantity Pledged (Margin)")) + _num(r.get("Quantity Pledged (Loan)"))
            if pledged:
                rep.warnings.append(f"{sym}: {pledged:g} shares pledged")
            if _num(r.get("Quantity Discrepant")):
                rep.warnings.append(f"{sym}: discrepant quantity — check with Zerodha")
            found = c.execute("SELECT security_id FROM securities WHERE isin=?", (isin,)).fetchone()
            if found:
                sid = found[0]
            else:
                c.execute("""INSERT INTO securities (market, symbol, name, isin, sector)
                             VALUES ('IN', ?, ?, ?, ?)
                             ON CONFLICT(market, symbol) DO UPDATE SET isin=excluded.isin""",
                          (sym, sym, isin, r.get("Sector") or r.get("Instrument Type")))
                sid = c.execute("SELECT security_id FROM securities WHERE market='IN' AND symbol=?",
                                (sym,)).fetchone()[0]
            c.execute("""INSERT OR REPLACE INTO holdings_snapshots
                         (snapshot_date, security_id, engine, quantity, avg_price)
                         VALUES (?, ?, 'investment', ?, ?)""",
                      (as_of, sid, qty, _num(r.get("Average Price")) or None))
            rep.positions += 1
    return rep
