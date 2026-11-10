import json
with open('scrip_master.json', 'r') as f:
    data = json.load(f)
    expiries = set()
    for item in data:
        if item.get('exch_seg') == 'NFO' and item.get('name') == 'NIFTY':
            expiries.add(item.get('expiry'))
    print(sorted(list(expiries)))
