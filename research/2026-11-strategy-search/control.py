"""Stage 1b (TRAIN only): random-entry controls for every exit, and edge = strategy R - random R."""
import sys, itertools, time; sys.path.insert(0, '/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad')
import pandas as pd, numpy as np
from load import grid
from v4.research import harness as H
S = '/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad'
g, _, _ = grid()
A, B = H.PERIODS["train"]
# rotation rerun with the look-ahead fix
rows = []
for top, mom, reb, reg in itertools.product([10, 20, 30], ["126", "252s", "252"], [21, 63], [False, True]):
    r = H.rotation(g, top=top, mom=mom, rebalance=reb, regime=reg, start=A, end=B)
    rows.append(dict(top=top, mom=mom, rebalance=reb, regime=reg, cagr=r["cagr"], mdd=r["mdd"]))
base = H.rotation(g, top=500, mom="252", rebalance=21, regime=False, start=A, end=B)
rr = pd.DataFrame(rows); rr["excess_vs_all"] = rr["cagr"] - base["cagr"]
rr.to_csv(f'{S}/train_rotation.csv', index=False)
print("baseline all", round(base["cagr"], 3))
# random-entry controls: density of a typical entry set
like = H.entry_mask(g, breakout=50, vol_mult=0, trend=True, rs="126", rs_top=0.2, regime=False, liq=0.4)
rnd = [H.random_mask(g, like, seed=s) for s in range(3)]
exits = list(itertools.product([("atr", 2.0), ("atr", 3.0), ("ll", 0)], [0.0, 2.0], ["ma20", "ma50", "chand", "none"], [20, 60, 250]))
ctrl = []
for (stop, k), tgt, trail, md in exits:
    tr = "ma" if trail.startswith("ma") else trail
    rs_ = []
    for m in rnd:
        t = H.simulate(g, m, stop=stop, stop_k=k or 2.0, max_risk=0.15, target_r=tgt, be=tgt > 0,
                       trail=tr, trail_ma=int(trail[2:]) if tr == "ma" else 20, max_days=md)
        rs_.append(H.score(t, "train")["avg_r"])
    ctrl.append(dict(stop=f"{stop}{k or ''}", target=tgt, trail=trail, max_days=md, random_r=np.mean(rs_)))
c = pd.DataFrame(ctrl); c.to_csv(f'{S}/train_controls.csv', index=False)
b = pd.read_csv(f'{S}/train_breakout.csv').merge(c, on=["stop", "target", "trail", "max_days"])
b["edge_r"] = b["avg_r"] - b["random_r"]
b.to_csv(f'{S}/train_breakout_edge.csv', index=False)
print("done")
