import os
import json
import pyotp
import pandas as pd
from SmartApi import SmartConnect
from dotenv import load_dotenv

load_dotenv()

def check_live_pnl():
    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_ID")
    password = os.getenv("ANGEL_PASSWORD")
    totp_token = os.getenv("ANGEL_TOTP_TOKEN")

    if not all([api_key, client_id, password, totp_token]):
        print("Missing Credentials!")
        return

    try:
        smart_api = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_token).now()
        data = smart_api.generateSession(client_id, password, totp)
        
        if not (data and data.get('status')):
            print(f"Login Failed: {data.get('message')}")
            return

        with open("active_trades_v3.json", "r") as f:
            trades = json.load(f)
            
        with open("broker_tokens_full.json", "r") as f:
            tokens_full = json.load(f)
            
        with open("broker_tokens.json", "r") as f:
            tokens_orig = json.load(f)

        print("\n--- LIVE P&L SNAPSHOT (Angel One API) ---")
        print(f"{'Symbol':<15} | {'Dir':<4} | {'Entry':<8} | {'LTP':<8} | {'Qty':<5} | {'PnL (INR)':<10}")
        print("-" * 70)
        
        total_pnl = 0.0
        
        for key, trade in trades.items():
            symbol = trade['symbol']
            direction = trade['direction']
            entry = float(trade['entry'])
            qty = int(trade['remaining_qty'])
            
            token = tokens_full.get(f"{symbol}-EQ") or tokens_orig.get(f"{symbol}-EQ")
            if not token:
                print(f"{symbol:<15} | {direction:<4} | {entry:<8.2f} | {'NO TOKEN':<8} | {qty:<5} | {'N/A':<10}")
                continue
            
            try:
                # ltpData uses exchange, tradingsymbol, symboltoken
                res = smart_api.ltpData("NSE", f"{symbol}-EQ", str(token))
                if res and res.get('status') and res.get('data'):
                    ltp = float(res['data']['ltp'])
                    
                    if direction == 'CE':
                        pnl = (ltp - entry) * qty
                    else: # PE
                        pnl = (entry - ltp) * qty
                        
                    total_pnl += pnl
                    print(f"{symbol:<15} | {direction:<4} | {entry:<8.2f} | {ltp:<8.2f} | {qty:<5} | {pnl:>10.2f}")
                else:
                    print(f"{symbol:<15} | {direction:<4} | {entry:<8.2f} | {'API ERR':<8} | {qty:<5} | {'N/A':<10}")
            except Exception as e:
                print(f"{symbol:<15} | {direction:<4} | {entry:<8.2f} | {'EXC':<8} | {qty:<5} | {'N/A':<10}")

        print("-" * 70)
        color = "\033[92m" if total_pnl >= 0 else "\033[91m"
        reset = "\033[0m"
        print(f"{'TOTAL RUNNING P&L':<51} | {color}{total_pnl:>10.2f} INR{reset}\n")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_live_pnl()
