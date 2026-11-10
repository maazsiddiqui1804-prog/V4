"""Stage 2: VALIDATION (2020–2022) for the pre-declared finalists only. Holdout is NOT touched."""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad')
import pandas as pd
from load import grid
from finalists import ROTATION, BREAKOUT
from v4.research import harness as H
g, _, _ = grid()
rows = []
for per in ["train", "valid"]:
    A, B = H.PERIODS[per]
    base = H.rotation(g, top=500, mom="252", rebalance=21, regime=False, start=A, end=B)
    idx = H.buy_hold_index(g, A, B)
    rows.append(dict(period=per, name="Equal-weight all stocks (survivor baseline)", cagr=base["cagr"], mdd=base["mdd"]))
    rows.append(dict(period=per, name="Nifty 500 index", cagr=idx["cagr"], mdd=idx["mdd"]))
    for name, kw in ROTATION.items():
        r = H.rotation(g, start=A, end=B, **kw)
        rows.append(dict(period=per, name=name, cagr=r["cagr"], mdd=r["mdd"]))
    for name, (e, x) in BREAKOUT.items():
        t = H.simulate(g, H.entry_mask(g, **e), **x)
        s = H.score(t, per); p = H.portfolio(t, start=A, end=B)
        rows.append(dict(period=per, name=name, cagr=p["cagr"], mdd=p["mdd"], n=s["n"], avg_r=s["avg_r"], win=s["win"]))
out = pd.DataFrame(rows)
out.to_csv('/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad/validation.csv', index=False)
pd.set_option('display.width', 200)
print(out.round(3).to_string())
