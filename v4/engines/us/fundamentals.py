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
    "debt_noncurrent": [("us-gaap", "LongTermDebtNoncurrent"), ("us-gaap", "LongTermDebtAndCapitalLeaseObligations"),
                        ("us-gaap", "LongTermDebt"),
                        ("ifrs-full", "NoncurrentPortionOfNoncurrentBorrowings"), ("ifrs-full", "LongtermBorrowings")],
    "debt_current": [("us-gaap", "LongTermDebtCurrent"), ("us-gaap", "LongTermDebtAndCapitalLeaseObligationsCurrent"),
                     ("us-gaap", "DebtCurrent"), ("us-gaap", "ShortTermBorrowings"),
                     ("ifrs-full", "CurrentPortionOfNoncurrentBorrowings"), ("ifrs-full", "ShorttermBorrowings")],
    "interest_expense": [("us-gaap", "InterestExpense"), ("us-gaap", "InterestExpenseNonoperating"),
                         ("ifrs-full", "FinanceCosts")],
    "eps_diluted": [("us-gaap", "EarningsPerShareDiluted"), ("ifrs-full", "DilutedEarningsLossPerShare")],
}
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F"}


def reporting_currency(facts: dict) -> str | None:
    """The currency the company reports in: the unit with the most annual revenue/profit rows
    in the last 5 years. Some foreign filers also tag USD 'convenience' figures (TSMC), which
    must not be mixed with their home-currency history."""
    from collections import Counter
    count: Counter = Counter()
    for item in ("revenue", "net_income"):
        for tax, concept in CONCEPTS[item]:
            node = facts.get("facts", {}).get(tax, {}).get(concept) or {}
            for unit, rows in node.get("units", {}).items():
                count[unit] += sum(1 for r in rows if r.get("form") in ANNUAL_FORMS and r.get("end", "") >= "2020")
    return count.most_common(1)[0][0] if count else None


def annual_series(facts: dict, item: str, currency: str | None = None) -> dict[str, float]:
    """{fiscal-year-end date: value} from annual reports.
    All label alternatives are merged (companies switch labels over time, e.g. Microsoft's revenue);
    for the same year an earlier-listed label wins, and within a label the latest filing wins.
    Only the reporting currency is used. Flow items (revenue, profit, cash flow) must cover ~a full year."""
    from datetime import date
    out: dict[str, tuple[int, str, float]] = {}
    for rank, (tax, concept) in enumerate(CONCEPTS[item]):
        node = facts.get("facts", {}).get(tax, {}).get(concept)
        if not node:
            continue
        for unit, rows in node.get("units", {}).items():
            if item == "eps_diluted":
                if currency and not unit.startswith(currency):
                    continue
            elif not unit.isalpha() or (currency and unit != currency):
                continue
            for r in rows:
                if r.get("form") not in ANNUAL_FORMS:
                    continue
                if "start" in r:                                   # flow item: keep ~12-month periods only
                    days = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
                    if not 350 <= days <= 380:
                        continue
                key = (-rank, r.get("filed", ""))
                prev = out.get(r["end"])
                if prev is None or key >= (prev[0], prev[1]):
                    out[r["end"]] = (key[0], key[1], float(r["val"]))
    return {k: v for k, (_, _, v) in sorted(out.items())}


def company(cik: int, years: int = 6) -> dict[str, dict[str, float]]:
    facts = sec.get(FACTS.format(cik=cik))
    cur = reporting_currency(facts)
    result = {}
    for item in CONCEPTS:
        s = annual_series(facts, item, cur)
        result[item] = dict(list(s.items())[-years:])
    result["_currency"] = cur or "unknown"
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
