import os
import json
import re
from datetime import datetime

def generate_frontend_inventory():
    inventory = {
        "phase": 2,
        "generated_at": datetime.now().isoformat(),
        "tabs": [],
        "ui_elements": [],
        "api_calls_used": [],
        "ws_subscriptions_used": [],
        "save_buttons_present": []
    }

    src_dir = os.path.join("AlgoTradingTelegramBotAndFrontend", "frontend", "src")
    comp_dir = os.path.join(src_dir, "components")

    # Scan App.jsx for tabs
    app_path = os.path.join(src_dir, "App.jsx")
    if os.path.exists(app_path):
        with open(app_path, 'r') as f:
            content = f.read()
            matches = re.findall(r"'([^']+)': <([^ ]+) />", content)
            for name, comp in matches:
                inventory["tabs"].append({"name": name, "component": comp})

    # Scan components for UI elements
    for f in os.listdir(comp_dir):
        if f.endswith(".jsx"):
            with open(os.path.join(comp_dir, f), 'r') as fp:
                content = fp.read()
                # Find buttons
                buttons = re.findall(r"<button[^>]*>([^<]+)</button>", content)
                for b in buttons:
                    inventory["ui_elements"].append({"tab": f, "type": "button", "label": b})
                
                # Find api calls
                api_calls = re.findall(r"api\.([a-z]+)\.([a-z]+)\(", content)
                for obj, method in api_calls:
                    inventory["api_calls_used"].append(f"{obj}.{method}")

    return inventory

if __name__ == "__main__":
    inv = generate_frontend_inventory()
    with open("frontend_inventory_v1.json", "w") as f:
        json.dump(inv, f, indent=2)
