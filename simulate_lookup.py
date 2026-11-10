import json
from datetime import datetime

file_path = 'scrip_master.json'
with open(file_path, 'r') as f:
    raw_data = json.load(f)

_data = {}
for item in raw_data:
    token = item.get('token')
    symbol = item.get('symbol')
    name = item.get('name')
    exch = item.get('exch_seg')
    if exch == 'NFO' and item.get('expiry'):
        try:
            expiry_raw = item.get('expiry') 
            expiry_dt = datetime.strptime(expiry_raw, '%d%b%Y')
            expiry_iso = expiry_dt.strftime('%Y-%m-%d')
            raw_strike = float(item.get('strike', 0))
            strike = raw_strike
            if strike >= 100000: 
                strike = strike / 100.0
            option_type = 'CE' if symbol.endswith('CE') else 'PE' if symbol.endswith('PE') else 'FUT'
            key = (name.upper(), expiry_iso, float(strike), option_type)
            _data[key] = token
        except Exception:
            continue

# Target check
target_key = ('NIFTY', '2026-05-26', 23950.0, 'CE')
print(f"Checking for {target_key}...")
if target_key in _data:
    print(f"FOUND: {target_key} -> {_data[target_key]}")
else:
    print("NOT FOUND")
    # Show similar keys
    print("Similar keys:")
    count = 0
    for k in _data:
        if k[0] == 'NIFTY' and k[1] == '2026-05-26':
            print(k)
            count += 1
            if count > 5: break
