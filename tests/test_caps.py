"""Checks combined India + US caps."""
import pytest
from v4.engines import caps


def H(name, sector, market, value):
    return {"name": name, "sector": sector, "market": market, "value": value}


def test_us_headroom_respects_30pct():
    h = [H("A", "IT", "IN", 70_000)]
    # total after cash = 100k, 30% = 30k, US now 0 → all 30k cash can go US
    assert caps.us_headroom(h, 85.0, 30_000) == pytest.approx(30_000)
    h.append(H("NVDA", "Chips", "US", 300))           # 300 USD × 85 = 25,500 INR
    assert caps.us_headroom(h, 85.0, 30_000) == pytest.approx(0.30 * 125_500 - 25_500)


def test_headroom_never_negative_or_above_cash():
    h = [H("NVDA", "Chips", "US", 1000)]
    assert caps.us_headroom(h, 85.0, 10_000) == 0.0
    assert caps.us_headroom([H("A", "IT", "IN", 1_000_000)], 85.0, 25_000) == 25_000


def test_check_flags_breaches_only_from_10_holdings():
    h = [H(f"S{i}", f"Sec{i}", "IN", 10_000) for i in range(9)] + [H("BIG", "Sec0", "IN", 50_000)]
    w = caps.check(h, 85.0)
    assert any("BIG" in x for x in w) and any("Sector Sec0" in x for x in w)
    assert caps.check(h[:5] + [h[-1]], 85.0) == []   # fewer than 10 holdings: % caps off
    us_heavy = [H("A", "IT", "IN", 10_000), H("N", "Chips", "US", 200)]
    assert "US share" in caps.check(us_heavy, 85.0)[0]
