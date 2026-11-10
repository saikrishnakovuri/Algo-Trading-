import os
import json
import time
from datetime import datetime, timedelta
from modules.broker_layer import AngelOneBroker

def test_api_limits():
    print("=== PART 1.1: TESTING ANGEL ONE API LIMITS ===")
    broker = AngelOneBroker()
    if not broker.login():
        print("Login failed.")
        return

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    token = token_map.get("HDFCBANK-EQ")
    
    test_intervals = {
        "ONE_MINUTE": [30, 40, 60, 90, 120],
        "FIVE_MINUTE": [60, 90, 120, 180, 365],
        "FIFTEEN_MINUTE": [90, 180, 365, 730],
        "ONE_DAY": [365, 730, 1460, 2000]
    }
    
    actual_limits = {}
    
    for interval, days_list in test_intervals.items():
        max_successful_days = 0
        for days in days_list:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            to_str = to_date.strftime('%Y-%m-%d %H:%M')
            from_str = from_date.strftime('%Y-%m-%d %H:%M')
            
            print(f"Testing {interval} for {days} days...")
            try:
                params = {
                    "exchange": "NSE",
                    "symboltoken": token,
                    "interval": interval,
                    "fromdate": from_str,
                    "todate": to_str
                }
                
                response = broker.smart_api.getCandleData(params)
                if response and response.get('status') and response.get('data'):
                    max_successful_days = days
                    print(f"  Success! Got {len(response['data'])} candles.")
                else:
                    msg = response.get('message') if response else 'No response'
                    print(f"  Failed at {days} days: {msg}")
                    break
            except Exception as e:
                print(f"  Exception at {days} days: {e}")
                break
            time.sleep(0.5)
            
        actual_limits[interval] = max_successful_days
        
    print("\nACTUAL API LIMITS:")
    for k, v in actual_limits.items():
        print(f"{k}: max {v} days")
        
    with open("api_limits.json", "w") as f:
        json.append(actual_limits, f)

if __name__ == '__main__':
    test_api_limits()
