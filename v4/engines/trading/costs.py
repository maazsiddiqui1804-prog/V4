"""Zerodha equity-delivery costs (D-047, D-093). Rates read from zerodha.com/charges on 2026-11-10.

Brokerage ₹0 · STT 0.1% buy and sell · NSE transaction 0.00307% · SEBI ₹10/crore ·
GST 18% on (brokerage + transaction + SEBI) · stamp 0.015% on buys · DP ₹15.34 per sell.
Slippage (PLACEHOLDER) is applied to fill prices separately, not here.
Income tax on gains (short-term) is estimated in reports, not deducted per trade.
"""
STT = 0.001
TXN = 0.0000307
SEBI = 10 / 1e7
GST = 0.18
STAMP = 0.00015
DP_PER_SELL = 15.34


def buy_cost(value: float) -> float:
    return value * (STT + TXN + SEBI + STAMP) + value * (TXN + SEBI) * GST


def sell_cost(value: float) -> float:
    return value * (STT + TXN + SEBI) + value * (TXN + SEBI) * GST + DP_PER_SELL
