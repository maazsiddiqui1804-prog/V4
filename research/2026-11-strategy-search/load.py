import sys, pickle; sys.path.insert(0, '/home/claude/v4-repo')
import pandas as pd
from v4.importers import india_prices as ip
from v4.research import harness as H
S = '/tmp/claude-0/-home-claude/0e33e368-5d0a-5083-897f-eb2d07e703c6/scratchpad/research'
def grid():
    px = pd.read_csv(f'{S}/india_daily.csv.gz', parse_dates=['date'])
    px, fixes = ip.fix_unadjusted(px)
    idx = pd.read_csv(f'{S}/nifty500_index.csv', parse_dates=['date']).set_index('date')['close']
    return H.Grid(px, idx), fixes, px
