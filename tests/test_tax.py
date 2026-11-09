"""Checks India capital-gains estimates."""
from v4.engines import tax


def test_short_and_long_term_split_with_exemption():
    sales = [{"buy_date": "2026-12-10", "sell_date": "2027-06-01", "gain": 50_000},     # short
             {"buy_date": "2026-12-10", "sell_date": "2028-01-15", "gain": 225_000}]    # long, FY2027-28
    out = tax.estimate(sales)
    assert out["FY2027-28"]["tax_estimate"] == round((50_000 * 0.20 + 100_000 * 0.125) * 1.04)


def test_exactly_one_year_is_still_short_term():
    out = tax.estimate([{"buy_date": "2027-01-01", "sell_date": "2028-01-01", "gain": 10_000}])
    assert out["FY2027-28"]["taxable_short"] == 10_000


def test_loss_set_off_rules():
    sales = [{"buy_date": "2027-05-01", "sell_date": "2027-08-01", "gain": -30_000},    # short-term loss
             {"buy_date": "2026-05-01", "sell_date": "2027-09-01", "gain": 200_000}]    # long-term gain
    out = tax.estimate(sales)["FY2027-28"]
    assert out["taxable_short"] == 0 and out["taxable_long"] == 200_000 - 30_000 - 125_000
    sales = [{"buy_date": "2026-05-01", "sell_date": "2027-08-01", "gain": -50_000},    # long-term loss
             {"buy_date": "2027-05-01", "sell_date": "2027-09-01", "gain": 40_000}]     # short-term gain
    out = tax.estimate(sales)["FY2027-28"]
    assert out["taxable_short"] == 40_000                                                # not reduced
