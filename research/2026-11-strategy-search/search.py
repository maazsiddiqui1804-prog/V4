"""Stage 1: search on TRAIN (2012–2019) only. Validation/holdout numbers are NOT computed here."""
import sys, itertools, time; sys.path.insert(0, '/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad')
import pandas as pd
from load import grid
from v4.research import harness as H
S = '/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad'
g, _, _ = grid()
A, B = H.PERIODS["train"]
rows = []
t0 = time.time()
# rotation family
for top, mom, reb, reg in itertools.product([10, 20, 30], ["126", "252s", "252"], [21, 63], [False, True]):
    r = H.rotation(g, top=top, mom=mom, rebalance=reb, regime=reg, start=A, end=B)
    rows.append(dict(family="rotation", top=top, mom=mom, rebalance=reb, regime=reg, cagr=r["cagr"], mdd=r["mdd"]))
base = H.rotation(g, top=500, mom="252", rebalance=21, regime=False, start=A, end=B)
rows.append(dict(family="baseline_equal_weight_all", cagr=base["cagr"], mdd=base["mdd"]))
idx = H.buy_hold_index(g, A, B)
rows.append(dict(family="baseline_nifty500_index", cagr=idx["cagr"], mdd=idx["mdd"]))
pd.DataFrame(rows).to_csv(f'{S}/train_rotation.csv', index=False)
print("rotation done", round(time.time() - t0), flush=True)

rows = []
entries = list(itertools.product([20, 50, 250], [0, 1.5], [None, "126", "252s"], [False, True]))
exits = list(itertools.product([("atr", 2.0), ("atr", 3.0), ("ll", 0)], [0.0, 2.0], ["ma20", "ma50", "chand", "none"], [20, 60, 250]))
for i, (bo, vm, rs, reg) in enumerate(entries):
    m = H.entry_mask(g, breakout=bo, vol_mult=vm, trend=True, rs=rs, rs_top=0.2, regime=reg, liq=0.4)
    for (stop, k), tgt, trail, md in exits:
        if trail == "none" and md == 250 and tgt == 0:
            continue
        tr = "ma" if trail.startswith("ma") else trail
        t = H.simulate(g, m, stop=stop, stop_k=k or 2.0, max_risk=0.15, target_r=tgt, be=tgt > 0,
                       trail=tr, trail_ma=int(trail[2:]) if tr == "ma" else 20, max_days=md)
        s = H.score(t, "train")
        if s.get("n", 0) >= 50:
            p = H.portfolio(t, start=A, end=B)
            s.update(cagr=p["cagr"], mdd=p["mdd"])
        rows.append(dict(family="breakout", breakout=bo, vol=vm, rs=rs, regime=reg, stop=f"{stop}{k or ''}",
                         target=tgt, trail=trail, max_days=md, **s))
    print(i + 1, "/", len(entries), round(time.time() - t0), flush=True)
    pd.DataFrame(rows).to_csv(f'{S}/train_breakout.csv', index=False)
print("done", round(time.time() - t0))
