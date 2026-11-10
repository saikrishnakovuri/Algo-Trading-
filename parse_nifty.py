import re
from datetime import datetime

log_file = r'logs\live_paper_controller.log'

entries = {}
trades = []

entry_pattern = re.compile(r'^(2026-05-22 \d{2}:\d{2}:\d{2}).*?\| INFO \| PAPER_ENTRY \| (NIFTY) \| (CE|PE) qty=(\d+) entry=([\d\.]+) sl=([\d\.]+) tp=([\d\.]+)')
exit_pattern = re.compile(r'^(2026-05-22 \d{2}:\d{2}:\d{2}).*?\| INFO \| PAPER_EXIT \| (NIFTY) \| pnl=([-\d\.]+) \| (\w+)')
strategy_pattern = re.compile(r'^(2026-05-22 \d{2}:\d{2}:\d{2}).*?\| INFO \| SIGNAL_PENDING \| (NIFTY) \| (\w+)')

last_strategies = {}

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        if '2026-05-22' not in line:
            continue
            
        m_strat = strategy_pattern.search(line)
        if m_strat:
            time_str, ticker, strategy = m_strat.groups()
            last_strategies[ticker] = strategy
            continue

        m_entry = entry_pattern.search(line)
        if m_entry:
            time_str, ticker, side, qty, entry_price, sl, tp = m_entry.groups()
            entries[ticker] = {
                'entry_time': time_str,
                'ticker': ticker,
                'side': side,
                'qty': qty,
                'entry_price': entry_price,
                'sl': sl,
                'tp': tp,
                'strategy': last_strategies.get(ticker, 'UNKNOWN')
            }
            continue
            
        m_exit = exit_pattern.search(line)
        if m_exit:
            time_str, ticker, pnl, reason = m_exit.groups()
            if ticker in entries:
                entry = entries.pop(ticker)
                
                # Calculate duration
                t1 = datetime.strptime(entry['entry_time'], '%Y-%m-%d %H:%M:%S')
                t2 = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                duration = t2 - t1
                
                trades.append({
                    'ticker': ticker,
                    'side': entry['side'],
                    'qty': entry['qty'],
                    'entry_time': entry['entry_time'],
                    'exit_time': time_str,
                    'duration': str(duration),
                    'entry_price': entry['entry_price'],
                    'exit_reason': reason,
                    'pnl': float(pnl),
                    'strategy': entry['strategy']
                })

print('| Ticker | Side | Qty | Entry Time | Exit Time | Duration | Strategy | Entry Price | PnL (₹) | Exit Reason |')
print('|---|---|---|---|---|---|---|---|---|---|')
total_pnl = 0
for t in trades:
    total_pnl += t['pnl']
    print(f"| {t['ticker']} | {t['side']} | {t['qty']} | {t['entry_time'].split()[1]} | {t['exit_time'].split()[1]} | {t['duration']} | {t['strategy']} | ₹{t['entry_price']} | {t['pnl']} | {t['exit_reason']} |")
print(f"**Total NIFTY PnL:** ₹{total_pnl}")
