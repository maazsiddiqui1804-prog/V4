# V4 — US investing tax check (D-131)

**Date:** 2026-11-09 · **Prepared by:** Claude (not tax advice) · **Status:** go-ahead given 2026-11-09 (D-132); safeguards built 2026-11-10 (shown in the app and monthly brief)
**Sources:** Zerodha support (global investing guide, ITR for US investments, charges), cross-checked with IRS and Income-tax Act summaries. Rules change; re-check yearly.

## How it works
- US stocks via Zerodha → BSE India INX Global Access (GIFT City); held with US broker ViewTrade (SIPC up to $500k), not in the Indian demat.
- Money goes out under LRS (cap $250k per financial year, all purposes combined). Netbanking only; min $50 first transfer, $100 after.
- Delivery only; fractional shares supported; US market hours ~7–8 PM to 1:30–2:30 AM IST. Stop-loss/GTT not live yet.

## The three checks
| Item | Rule | What it means for V4 |
|---|---|---|
| **TCS on remittance** | 20% on LRS remittances above ₹10 lakh per financial year (Zerodha; since 1 Apr 2025). Adjustable against tax or refunded in ITR — not an extra tax. ⚠️ One summary of the new Income-tax Act 2025 (Sec 394) lists 20% for investment remittances without clearly stating the ₹10L threshold — re-verify before the first transfer. | At ₹25k/month with US ≤30% of the investment sleeve (D-089), US remittances stay far below ₹10L/yr. Worst case (no threshold): 20% is held back as a tax credit, not lost. **Built:** yearly remittance tracker warns at 80% of the threshold. |
| **Schedule FA (foreign assets)** | Must declare US stocks, ETFs and wallet cash in the ITR, **calendar-year basis**, even with no sales. Non-disclosure → Black Money Act penalties/prosecution. Use ITR-2 (ITR-3 if business income). Also Schedule CG, OS (dividends), FSI, TR + Form 67 (foreign tax credit). | Nothing needed at purchase. One-off professional/tax-service review before the **first ITR that includes US shares** (~mid-2027). **Built:** calendar-year holdings log (initial, peak, closing value). |
| **US estate tax** | Applies if US-situs assets exceed **$60,000** at death (non-US residents); 18–40%; no India–US estate treaty (IRS confirms $60k Form 706-NA threshold; US-company stock is US-situs). Irish-domiciled ETFs are not US-situs. | Years away at current sizing. **Built:** warning when US holdings pass ~$45k. |

## Other tax and cost facts
- **Gains:** long-term only after **>24 months**; LTCG 12.5% + surcharge/cess, no ₹1.25L exemption, no indexation; short-term at slab rate. Computed in INR at SBI TT buying rate (last day of previous month).
- **Dividends:** 25% US withholding with a valid **Form W-8BEN** (renew every ~3 years; **built:** reminder before expiry — submit before the first US buy, T-058); claim credit in India via Form 67 + Schedule TR.
- **Costs:** brokerage 0.10% (max $10/order) + 18% GST; small IFSCA/SEC/FINRA fees; currency markup 0.4–1.4% over RBI rate; conversion fee ₹45 flat up to ₹25k, then tiered %, +GST; bank wire fee varies. No account or maintenance fee; idle wallet cash free up to 180 days.
- **Advance tax** applies if total tax for the year exceeds ₹10,000.

## Still open
1. Small monthly transfers are relatively expensive (₹45 flat fee + markup on ~₹7.5k ≈ 1–2%) → monthly vs quarterly US transfers is Maaz's decision (T-056).
2. Re-verify the TCS ₹10L threshold under the Income-tax Act 2025 before the first transfer.
