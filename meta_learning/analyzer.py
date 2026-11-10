from collections import defaultdict
import numpy as np

def compute_metrics(pnls):
    """Computes win rate, expectancy, consistency, and total trades."""
    if not pnls:
        return {"win_rate": 0, "expectancy": 0, "consistency": 0, "trades": 0}
        
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(pnls)
    avg_win = sum(wins)/len(wins) if wins else 0
    avg_loss = abs(sum(losses)/len(losses)) if losses else 0

    # Expectancy = (Win% * AvgWin) - (Loss% * AvgLoss)
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    # Consistency = Profitable Trades / Total Trades
    consistency = len(wins) / len(pnls)

    return {
        "win_rate": round(win_rate * 100, 2),
        "expectancy": round(expectancy, 2),
        "consistency": round(consistency, 2),
        "trades": len(pnls)
    }

def analyze(trades):
    """Analyzes trade database and groups performance with sub-windows."""
    stats = {
        "by_stock": defaultdict(list),
        "by_setup": defaultdict(list),
        "by_time_window": defaultdict(list), # Sub-windows: 'Early' vs 'Late'
    }

    for t in trades:
        stats["by_stock"][t["symbol"]].append(t["pnl"])
        stats["by_setup"][t.get("setup", "UNKNOWN")].append(t["pnl"])
        
        # Time Window Split
        if " " in t["date"]:
            time_str = t["date"].split(" ")[1]
            h, m = map(int, time_str.split(":"))
            total_mins = h * 60 + m
            # 9:15 - 9:45 = Early Volatility
            if total_mins <= (9 * 60 + 45):
                window = "EARLY_VOLATILITY (09:15-09:45)"
            else:
                window = "STRUCTURED_MOVE (09:45-10:30)"
            stats["by_time_window"][window].append(t["pnl"])

    return stats
