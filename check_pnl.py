
import os
import json
import yaml
from modules.broker_layer import AngelOneBroker

def check_current_pnl():
    broker = AngelOneBroker()
    if not broker.login():
        print("Login failed")
        return

    if not os.path.exists("active_trades.json"):
        print("No active trades")
        return

    with open("active_trades.json", "r") as f:
        active_trades = json.load(f)

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    total_pnl = 0
    print("\n--- CURRENT FLOATING P&L ---")
    print(f"{'Symbol':<12} | {'Entry':<8} | {'LTP':<8} | {'Qty':<6} | {'PnL':<10}")
    print("-" * 55)

    for key, trade in active_trades.items():
        symbol = trade['symbol']
        entry = trade['entry']
        qty = trade['remaining_qty']
        direction = trade['direction']
        
        angel_sym = f"{symbol}-EQ"
        token = token_map.get(angel_sym)
        
        if token:
            res = broker.get_market_data("NSE", angel_sym, token)
            if res and res.get('status'):
                ltp = float(res['data']['ltp'])
                pnl = (ltp - entry) * qty if direction == 'CE' else (entry - ltp) * qty
                total_pnl += pnl
                print(f"{symbol:<12} | {entry:<8.2f} | {ltp:<8.2f} | {qty:<6} | {pnl:<+10.2f} INR")
            else:
                print(f"{symbol:<12} | Data Fetch Error")

    print("-" * 55)
    print(f"{'TOTAL P&L':<39} | {total_pnl:<+10.2f} INR")
    print("-" * 55)

if __name__ == "__main__":
    check_current_pnl()
