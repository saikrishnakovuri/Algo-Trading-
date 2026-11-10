import json
from datetime import datetime
import collections

trade_file = 'data/live_paper_trades.json'

with open(trade_file, 'r') as f:
    trades = json.load(f)

# Filter out only CLOSED trades to show complete lifecycle
closed_trades = [t for t in trades if t.get('status') == 'CLOSED']

# Sort by opened_at
closed_trades.sort(key=lambda x: x.get('opened_at', ''))

def parse_time(t_str):
    if not t_str: return None
    try:
        # Handles 2026-05-18T12:00:22.593871 or 2026-05-18T12:00:00
        return datetime.fromisoformat(t_str)
    except ValueError:
        return None

def format_duration(delta):
    if not delta: return "N/A"
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    rem_sec = seconds % 60
    if minutes < 60:
        return f"{minutes}m {rem_sec}s"
    hours = minutes // 60
    rem_min = minutes % 60
    return f"{hours}h {rem_min}m"

dates_to_show = ["2026-05-20", "2026-05-19", "2026-05-18"]

for target_date in dates_to_show:
    day_trades = [t for t in closed_trades if t.get('opened_at', '').startswith(target_date)]
    if not day_trades:
        print(f"\n### Trades for {target_date}: None found.")
        continue
        
    print(f"\n### Trades for {target_date}")
    print(f"| Entry Time | Symbol | Side | Exit Time | Duration | Exit Price | P&L | Strategy |")
    print(f"| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- |")
    
    for t in day_trades:
        entry_time_full = parse_time(t.get('opened_at'))
        exit_time_full = parse_time(t.get('closed_at'))
        
        entry_time = entry_time_full.strftime('%H:%M:%S') if entry_time_full else "N/A"
        exit_time = exit_time_full.strftime('%H:%M:%S') if exit_time_full else "N/A"
        
        duration = "N/A"
        if entry_time_full and exit_time_full:
            duration = format_duration(exit_time_full - entry_time_full)
            
        symbol = t.get('symbol', 'N/A')
        side = t.get('side', 'N/A')
        exit_p = t.get('exit_price', 0.0)
        pnl = t.get('pnl', 0.0)
        strat = t.get('strategy', 'N/A')
        
        print(f"| {entry_time} | {symbol} | {side} | {exit_time} | {duration} | {exit_p:.2f} | {pnl:.2f} | {strat} |")

