# Strategy search — Nov 2026 (HISTORICAL SIMULATION, NOT LIVE)

Asked by Maaz 2026-11-10: "run simulations that make money; fix the strategy that makes money".

Protocol (fixed before results): today's Nifty 500, Yahoo prices 2011-11→2026-11 (split fixes),
costs 0.35% round trip + 0.1% slippage each side, next-morning-open entries, gap fills at the open.
1. Search on TRAIN 2012–2019 only (36 rotation + 2,484 breakout variants) → `train_*.csv`.
2. Finalists declared in `finalists.py` (time in `finalists.declared_at`) → VALID 2020–2022 → `validation.csv`.
3. Pass criteria written in `holdout_criteria.txt` → HOLDOUT 2023–2026 run once → `holdout.csv`.
4. Diagnostic: random-entry control with identical exits → `edge.csv`.

Survivorship: today's index list flatters every long strategy (equal-weight survivors earned
~21%/yr in 2023–26 vs 11% for the real Nifty 500). Read results as edge over the random/equal-weight controls.
Data on branch `research-data` (not main). Harness: `v4/research/harness.py`.
