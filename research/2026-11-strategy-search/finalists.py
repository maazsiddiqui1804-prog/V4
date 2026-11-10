"""Pre-declared finalists, chosen on TRAIN (2012–2019) only, written before any validation run.
Selection rule: rotation = best train CAGR plus two robust neighbours and the market-filter variant;
breakout = best portfolio CAGR among configs with >=300 train trades and edge over random entries > 0.3R.
C0 = current V4 trading rules for reference."""
ROTATION = {
    "R1 top10 6m monthly":            dict(top=10, mom="126", rebalance=21, regime=False),
    "R2 top20 12m monthly":           dict(top=20, mom="252", rebalance=21, regime=False),
    "R3 top20 6m monthly":            dict(top=20, mom="126", rebalance=21, regime=False),
    "R4 top10 6m monthly +mkt filter": dict(top=10, mom="126", rebalance=21, regime=True),
}
BREAKOUT = {
    "B1 52w high, vol, 12m RS, ATR2 stop, trail 50dma":
        (dict(breakout=250, vol_mult=1.5, trend=True, rs="252s", rs_top=0.2, regime=False, liq=0.4),
         dict(stop="atr", stop_k=2.0, max_risk=0.15, target_r=0.0, be=False, trail="ma", trail_ma=50, max_days=250)),
    "B2 = B1 + market filter":
        (dict(breakout=250, vol_mult=1.5, trend=True, rs="252s", rs_top=0.2, regime=True, liq=0.4),
         dict(stop="atr", stop_k=2.0, max_risk=0.15, target_r=0.0, be=False, trail="ma", trail_ma=50, max_days=250)),
    "B3 50d high, vol, 12m RS, ATR2 stop, trail 50dma":
        (dict(breakout=50, vol_mult=1.5, trend=True, rs="252s", rs_top=0.2, regime=False, liq=0.4),
         dict(stop="atr", stop_k=2.0, max_risk=0.15, target_r=0.0, be=False, trail="ma", trail_ma=50, max_days=250)),
    "C0 current V4 rules":
        (dict(breakout=20, vol_mult=1.5, trend=True, rs="126", rs_top=0.2, regime=False, liq=0.4, stretch=0.10),
         dict(stop="ll", max_risk=0.10, target_r=2.0, be=False, trail="ma", trail_ma=20, trail_after_partial=True, max_days=20)),
}
