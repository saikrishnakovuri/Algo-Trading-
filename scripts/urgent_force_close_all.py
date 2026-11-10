import os
import json
import pyotp
import pandas as pd
import csv
from datetime import datetime
from SmartApi import SmartConnect
from dotenv import load_dotenv

load_dotenv()

def force_close_all():
    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_ID")
    password = os.getenv("ANGEL_PASSWORD")
    totp_token = os.getenv("ANGEL_TOTP_TOKEN")

    if not all([api_key, client_id, password, totp_token]):
        print("Missing Credentials!")
        return

    try:
        # 1. Login to get live prices
        smart_api = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_token).now()
        data = smart_api.generateSession(client_id, password, totp)
        
        if not (data and data.get('status')):
            print(f"Login Failed: {data.get('message')}")
            return

        # 2. Load active trades
        if not os.path.exists("active_trades_v3.json"):
            print("No active trades file found.")
            return
            
        with open("active_trades_v3.json", "r") as f:
            active_trades = json.load(f)
            
        if not active_trades:
            print("No active trades found.")
            return

        # 3. Load tokens
        tokens = {}
        if os.path.exists("broker_tokens_full.json"):
            tokens.update(json.load(open("broker_tokens_full.json")))
        if os.path.exists("broker_tokens.json"):
            tokens.update(json.load(open("broker_tokens.json")))

        JOURNAL_FILE = "trade_journal_v3_ws.csv"
        JOURNAL_HEADERS = ['date', 'time', 'symbol', 'strategy', 'pattern', 'direction', 'entry', 'sl', 'target', 'exit_price', 'exit_type', 'pnl', 'r_multiple', 'confidence', 'score', 'bars_held']

        print(f"\n🚀 URGENT: Closing {len(active_trades)} positions at Market LTP...")
        print("-" * 50)

        for key, trade in list(active_trades.items()):
            symbol = trade['symbol']
            token = tokens.get(f"{symbol}-EQ")
            
            if not token:
                print(f"❌ Error: No token for {symbol}. Skipping.")
                continue

            try:
                res = smart_api.ltpData("NSE", f"{symbol}-EQ", str(token))
                if res and res.get('status') and res.get('data'):
                    ltp = float(res['data']['ltp'])
                    entry = float(trade['entry'])
                    qty = int(trade['remaining_qty'])
                    direction = trade['direction']

                    # Calculate P&L
                    if direction == 'CE':
                        pnl = (ltp - entry) * qty
                    else:
                        pnl = (entry - ltp) * qty

                    # Write to Journal
                    trade_info = {
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'symbol': symbol,
                        'strategy': trade.get('strategy', 'UNKNOWN'),
                        'pattern': trade.get('pattern', ''),
                        'direction': direction,
                        'entry': entry,
                        'sl': trade.get('current_sl', 0),
                        'target': ltp,
                        'exit_price': ltp,
                        'exit_type': 'MANUAL_FORCE_CLOSE',
                        'pnl': round(pnl, 2),
                        'r_multiple': 0.0, # Simplified
                        'confidence': trade.get('confidence', 0),
                        'score': trade.get('score', 0),
                        'bars_held': ''
                    }

                    file_exists = os.path.exists(JOURNAL_FILE)
                    with open(JOURNAL_FILE, 'a', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=JOURNAL_HEADERS, extrasaction='ignore')
                        if not file_exists: writer.writeheader()
                        writer.writerow(trade_info)

                    print(f"✅ CLOSED {symbol:<12} | PnL: {pnl:>10.2f} INR")
                    
                    # Remove from active list
                    del active_trades[key]
                else:
                    print(f"❌ API Error for {symbol}. Could not fetch LTP.")
            except Exception as e:
                print(f"❌ Exception closing {symbol}: {e}")

        # 4. Save the empty state
        with open("active_trades_v3.json", "w") as f:
            json.dump(active_trades, f, indent=2)

        print("-" * 50)
        print("🏁 All positions handled. Active trades state cleared.\n")

    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    force_close_all()
