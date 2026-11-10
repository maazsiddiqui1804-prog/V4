"""Diagnostic (no tuning): random-entry control with the SAME exits and the SAME number of entries per day,
per period, to separate real edge from survivorship drift."""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad')
import numpy as np, pandas as pd
from load import grid
from finalists import BREAKOUT
from v4.research import harness as H
g, _, _ = grid()
rows = []
for name, (e, x) in BREAKOUT.items():
    m = H.entry_mask(g, **e)
    t = H.simulate(g, m, **x)
    rnd = [H.simulate(g, H.random_mask(g, m, seed=s), **x) for s in range(5)]
    for per in ["train", "valid", "holdout"]:
        A, B = H.PERIODS[per]
        rr = [H.score(r, per)["avg_r"] for r in rnd]
        rp = [H.portfolio(r, start=A, end=B)["cagr"] for r in rnd]
        rows.append(dict(name=name[:3], period=per, strat_r=H.score(t, per)["avg_r"], random_r=np.mean(rr),
                         strat_cagr=H.portfolio(t, start=A, end=B)["cagr"], random_cagr=np.mean(rp)))
d = pd.DataFrame(rows); d["edge_r"] = d.strat_r - d.random_r; d["edge_cagr"] = d.strat_cagr - d.random_cagr
print(d.round(3).to_string())
d.to_csv('/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad/edge.csv', index=False)
