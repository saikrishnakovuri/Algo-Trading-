import json
with open('scrip_master.json', 'r') as f:
    data = json.load(f)
    found = 0
    for item in data:
        if item.get('exch_seg') == 'NFO' and item.get('name') == 'NIFTY' and '28MAY' in item.get('expiry', ''):
            print(item)
            found += 1
            if found >= 5:
                break
