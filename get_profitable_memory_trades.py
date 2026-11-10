import json
from datetime import datetime

trade_file = 'data/live_paper_trades.json'

with open(trade_file, 'r') as f:
    trades = json.load(f)

# Dates to consider
dates_to_show = ["2026-05-20", "2026-05-19", "2026-05-18"]

# Filter out only CLOSED, Profitable trades for MARKET_MEMORY strategy
profitable_memory_trades = [
    t for t in trades 
    if t.get('status') == 'CLOSED' 
    and t.get('strategy') == 'MARKET_MEMORY'
    and t.get('pnl', 0) > 0
    and any(t.get('opened_at', '').startswith(d) for d in dates_to_show)
]

# Sort by date
profitable_memory_trades.sort(key=lambda x: x.get('opened_at', ''))

def parse_time(t_str):
    if not t_str: return None
    try:
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

print("### Profitable MARKET_MEMORY Trades (Last 3 Days)")
print("*(Note: MARKET_MEMORY handles confidence internally based on level sweeps/retests rather than a fixed technical threshold. Baseline confidence starts at 52-60 and scales up to 95 based on confirmation hits.)*")
print("\n| Date/Time | Symbol | Side | Duration | Entry | Exit | Net P&L (₹) |")
print("| :--- | :--- | :---: | :--- | :--- | :--- | :--- |")

for t in profitable_memory_trades:
    entry_time_full = parse_time(t.get('opened_at'))
    exit_time_full = parse_time(t.get('closed_at'))
    
    entry_time = entry_time_full.strftime('%m-%d %H:%M:%S') if entry_time_full else "N/A"
    duration = "N/A"
    if entry_time_full and exit_time_full:
        duration = format_duration(exit_time_full - entry_time_full)
        
    symbol = t.get('symbol', 'N/A')
    side = t.get('side', 'N/A')
    entry_p = t.get('entry_price', 0.0)
    exit_p = t.get('exit_price', 0.0)
    pnl = t.get('pnl', 0.0)
    
    print(f"| {entry_time} | {symbol} | {side} | {duration} | {entry_p:.2f} | {exit_p:.2f} | **{pnl:.2f}** |")

print(f"\n**Total Profitable MARKET_MEMORY Trades:** {len(profitable_memory_trades)}")
