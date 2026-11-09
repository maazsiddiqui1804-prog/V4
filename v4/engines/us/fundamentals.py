"""US fundamentals from SEC XBRL 'companyfacts' (D-096). Annual figures only.

Plain English: every US-listed company files its financials with SEC in a
machine-readable form. This pulls the yearly numbers V4's US score needs:
revenue, operating profit, net profit, operating cash flow, total assets,
current liabilities, equity, debt, interest expense, diluted EPS.
US companies use US-GAAP labels; foreign filers (TSMC, ASML) use IFRS labels,
so each item has a short list of label alternatives, tried in order.
"""
from __future__ import annotations

import sys

from v4.importers import sec

FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# item -> list of (taxonomy, concept) alternatives, tried in order
CONCEPTS = {
    "revenue": [("us-gaap", "Revenues"), ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
                ("us-gaap", "SalesRevenueNet"), ("ifrs-full", "Revenue")],
    "operating_income": [("us-gaap", "OperatingIncomeLoss"), ("ifrs-full", "ProfitLossFromOperatingActivities")],
    "net_income": [("us-gaap", "NetIncomeLoss"), ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"),
                   ("ifrs-full", "ProfitLoss")],
    "cfo": [("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
            ("ifrs-full", "CashFlowsFromUsedInOperatingActivities")],
    "assets": [("us-gaap", "Assets"), ("ifrs-full", "Assets")],
    "current_liabilities": [("us-gaap", "LiabilitiesCurrent"), ("ifrs-full", "CurrentLiabilities")],
    "equity": [("us-gaap", "StockholdersEquity"), ("ifrs-full", "EquityAttributableToOwnersOfParent"),
               ("ifrs-full", "Equity")],
    "debt_noncurrent": [("us-gaap", "LongTermDebtNoncurrent"), ("ifrs-full", "NoncurrentPortionOfNoncurrentBorrowings"),
                        ("ifrs-full", "LongtermBorrowings")],
    "debt_current": [("us-gaap", "LongTermDebtCurrent"), ("ifrs-full", "CurrentPortionOfNoncurrentBorrowings"),
                     ("ifrs-full", "ShorttermBorrowings")],
    "interest_expense": [("us-gaap", "InterestExpense"), ("us-gaap", "InterestExpenseNonoperating"),
                         ("ifrs-full", "FinanceCosts")],
    "eps_diluted": [("us-gaap", "EarningsPerShareDiluted"), ("ifrs-full", "DilutedEarningsLossPerShare")],
}
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F"}


def annual_series(facts: dict, item: str) -> dict[str, float]:
    """{fiscal-year-end date: value} from annual reports; the latest filing wins.
    Flow items (revenue, profit, cash flow) must cover ~a full year."""
    from datetime import date
    for tax, concept in CONCEPTS[item]:
        node = facts.get("facts", {}).get(tax, {}).get(concept)
        if not node:
            continue
        out: dict[str, tuple[str, float]] = {}
        for unit, rows in node.get("units", {}).items():
            if item != "eps_diluted" and not unit.isalpha():      # currency units only (USD, TWD, EUR…)
                continue
            for r in rows:
                if r.get("form") not in ANNUAL_FORMS:
                    continue
                if "start" in r:                                   # flow item: keep ~12-month periods only
                    days = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
                    if not 350 <= days <= 380:
                        continue
                prev = out.get(r["end"])
                if prev is None or r.get("filed", "") >= prev[0]:
                    out[r["end"]] = (r.get("filed", ""), float(r["val"]))
        if out:
            return {k: v for k, (_, v) in sorted(out.items())}
    return {}


def company(cik: int, years: int = 6) -> dict[str, dict[str, float]]:
    facts = sec.get(FACTS.format(cik=cik))
    result = {}
    for item in CONCEPTS:
        s = annual_series(facts, item)
        result[item] = dict(list(s.items())[-years:])
    result["_currency"] = next(iter(facts.get("facts", {}).get("ifrs-full", {}) and ["non-USD (IFRS)"] or ["USD"]))
    return result


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "probe":
        tmap = sec.ticker_map()
        for t in sys.argv[2].split(","):
            data = company(tmap[t.upper()], years=4)
            print(f"== {t} ({data.pop('_currency')})")
            for item, series in data.items():
                vals = ", ".join(f"{d[:7]}: {v:,.4g}" for d, v in series.items()) or "— missing"
                print(f"   {item:20} {vals}")
