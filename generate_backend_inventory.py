import os
import json
import re
from datetime import datetime

def generate_inventory():
    inventory = {
        "phase": 1,
        "generated_at": datetime.now().isoformat(),
        "api_endpoints": [],
        "websocket_endpoints": [],
        "config_fields": [],
        "v3_utils_constants": [],
        "data_file_fields": [],
        "strategy_components": [],
        "log_levels_observed": ["INFO", "WARNING", "ERROR", "DEBUG"],
        "notification_types": [
            {"type": "trade_entry", "channel": "telegram"},
            {"type": "trade_exit", "channel": "telegram"}
        ],
        "subprocess_capabilities": [
            {"action": "start_live_trader", "command": "python live_options_trader.py"},
            {"action": "stop_live_trader", "command": "SIGTERM"},
            {"action": "run_backtest", "command": "python main_backtest.py"}
        ]
    }

    # Scan routers
    router_dir = os.path.join("AlgoTradingTelegramBotAndFrontend", "backend", "routers")
    for f in os.listdir(router_dir):
        if f.endswith(".py") and f != "__init__.py":
            with open(os.path.join(router_dir, f), 'r') as fp:
                content = fp.read()
                # Find @router.get/post
                matches = re.findall(r'@router\.(get|post|websocket)\("([^"]+)"\)', content)
                for method, path in matches:
                    if method == "websocket":
                        inventory["websocket_endpoints"].append({
                            "path": path,
                            "purpose": f"WS in {f}"
                        })
                    else:
                        inventory["api_endpoints"].append({
                            "method": method.upper(),
                            "path": path,
                            "router": f,
                            "purpose": f"Endpoint in {f}"
                        })

    # Scan v3_utils
    v3_utils_path = os.path.join("modules", "v3_utils.py")
    if os.path.exists(v3_utils_path):
        with open(v3_utils_path, 'r') as fp:
            content = fp.read()
            matches = re.findall(r'^([A-Z][A-Z0-9_]+)\s*=', content, re.MULTILINE)
            for name in matches:
                inventory["v3_utils_constants"].append({"name": name})

    # Scan config dir
    config_dir = "config"
    if os.path.exists(config_dir):
        for f in os.listdir(config_dir):
            if f.endswith(".yaml"):
                inventory["config_fields"].append({"file": f"config/{f}", "path": "root"})

    return inventory

if __name__ == "__main__":
    inv = generate_inventory()
    with open("backend_inventory_v1.json", "w") as f:
        json.dump(inv, f, indent=2)
