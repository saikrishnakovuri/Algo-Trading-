from pathlib import Path
import csv
from decimal import Decimal
from collections import defaultdict
path = Path(r'C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\optimized_backtest_results_jan.csv')
rows = []
with path.open('r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

total = len(rows)
win = sum(1 for r in rows if r['result']=='WIN')
lose = sum(1 for r in rows if r['result']=='LOSS')
pnl = sum(Decimal(r['pnl']) for r in rows)
pnl_pct = sum(Decimal(r['pnl_pct']) for r in rows)
by_strategy = defaultdict(lambda: {'count':0,'win':0,'lose':0,'pnl':Decimal(0),'avg_pct':Decimal(0)})
by_conf = defaultdict(lambda: {'count':0,'win':0,'lose':0,'pnl':Decimal(0)})
for r in rows:
    s = by_strategy[r['strategy']]
    s['count'] += 1
    if r['result']=='WIN': s['win'] += 1
    elif r['result']=='LOSS': s['lose'] += 1
    s['pnl'] += Decimal(r['pnl'])
    s['avg_pct'] += Decimal(r['pnl_pct'])
    c = by_conf[r['confidence']]
    c['count'] += 1
    if r['result']=='WIN': c['win'] += 1
    elif r['result']=='LOSS': c['lose'] += 1
    c['pnl'] += Decimal(r['pnl'])

print('TOTAL_ROWS', total)
print('WINS', win, 'LOSES', lose, 'WIN_RATE%', round(win/total*100,2))
print('TOTAL_PNL', round(pnl,2), 'AVG_PNL_PER_TRADE', round(pnl/total,2), 'AVG_PNL_PCT_PER_TRADE', round(pnl_pct/total,6))
print('\nTOP_STRATEGIES_BY_COUNT')
for strat, stats in sorted(by_strategy.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
    wr = stats['win']/stats['count']*100 if stats['count'] else 0
    avg_pct = stats['avg_pct']/stats['count']
    print(f"{strat}: count={stats['count']}, win%={wr:.1f}, pnl={stats['pnl']:.2f}, avg_pct={avg_pct:.4f}")
print('\nTOP_STRATEGIES_BY_PNL')
for strat, stats in sorted(by_strategy.items(), key=lambda x: x[1]['pnl'], reverse=True)[:10]:
    wr = stats['win']/stats['count']*100 if stats['count'] else 0
    avg_pct = stats['avg_pct']/stats['count']
    print(f"{strat}: count={stats['count']}, win%={wr:.1f}, pnl={stats['pnl']:.2f}, avg_pct={avg_pct:.4f}")
print('\nCONFIDENCE_BUCKETS')
for conf, stats in sorted(by_conf.items(), key=lambda x: float(x[0])):
    wr = stats['win']/stats['count']*100 if stats['count'] else 0
    print(f"{conf}: count={stats['count']}, win%={wr:.1f}, pnl={stats['pnl']:.2f}")
