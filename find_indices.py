
import json

with open('scrip_master.json', 'r') as f:
    data = json.load(f)

indices = ["26000", "99926000", "26009", "99926009", "26017", "99926017"]

for item in data:
    if item.get('token') in indices:
        print(f"Token: {item.get('token')} | Symbol: {item.get('symbol')} | Name: {item.get('name')} | Exch: {item.get('exch_seg')}")
