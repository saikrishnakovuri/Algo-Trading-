import json
import os
import re
import yaml
import datetime
from pathlib import Path
import ast

def extract_endpoints(file_path):
    if not os.path.exists(file_path): return []
    endpoints = []
    content = open(file_path, "r", encoding="utf-8").read()
    
    # regex for @app.xxx or @router.xxx
    pattern = r'@(?:app|api_router|router)\.(get|post|put|delete|websocket|patch)\(.*?["\'](.*?)["\']'
    matches = re.finditer(pattern, content)
    
    for match in matches:
        method = match.group(1).upper()
        path = match.group(2)
        purpose = f"{method} {path}"
        endpoints.append({
            "method": method,
            "path": path,
            "router": os.path.basename(file_path),
            "request_params": [],
            "response_shape": {},
            "purpose": purpose
        })
    return endpoints

def extract_websocket_endpoints(file_path):
    if not os.path.exists(file_path): return []
    endpoints = []
    content = open(file_path, "r", encoding="utf-8").read()
    
    pattern = r'@(?:app|api_router|router)\.websocket\(.*?["\'](.*?)["\']'
    matches = re.finditer(pattern, content)
    
    for match in matches:
        path = match.group(1)
        endpoints.append({
            "path": path,
            "push_shape": {},
            "push_frequency_sec": 0,
            "purpose": f"WS {path}"
        })
    return endpoints

def extract_public_functions(file_path):
    if not os.path.exists(file_path): return []
    functions = []
    try:
        content = open(file_path, "r", encoding="utf-8").read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                functions.append(node.name)
    except Exception as e:
        print(f"AST Error in {file_path}: {e}")
    return functions

def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def extract_yaml_fields(config_dir):
    fields = []
    if not os.path.exists(config_dir): return fields
    
    for file in os.listdir(config_dir):
        if file.endswith(".yaml"):
            file_path = os.path.join(config_dir, file)
            try:
                data = yaml.safe_load(open(file_path, "r"))
                if data:
                    flat = flatten_dict(data)
                    for k, v in flat.items():
                        fields.append({
                            "file": f"config/{file}",
                            "path": k,
                            "type": type(v).__name__,
                            "default": v,
                            "purpose": f"Config field {k}"
                        })
            except Exception as e:
                pass
    return fields

def extract_constants(file_path):
    constants = []
    if not os.path.exists(file_path): return constants
    try:
        content = open(file_path, "r", encoding="utf-8").read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constants.append({
                            "name": target.id,
                            "type": "any",
                            "default": None
                        })
    except:
        pass
    return constants

def main():
    root = ".."
    backend_dir = os.path.join(root, "AlgoTradingTelegramBotAndFrontend", "backend")
    
    # 1. API Endpoints
    api_endpoints = []
    ws_endpoints = []
    server_py = os.path.join(backend_dir, "server.py")
    api_endpoints.extend(extract_endpoints(server_py))
    ws_endpoints.extend(extract_websocket_endpoints(server_py))
    
    routers_dir = os.path.join(backend_dir, "routers")
    if os.path.exists(routers_dir):
        for f in os.listdir(routers_dir):
            if f.endswith(".py"):
                api_endpoints.extend(extract_endpoints(os.path.join(routers_dir, f)))
                ws_endpoints.extend(extract_websocket_endpoints(os.path.join(routers_dir, f)))

    # 2. Config fields
    config_dir = os.path.join(root, "config")
    config_fields = extract_yaml_fields(config_dir)

    # 3. v3_utils constants
    v3_utils_path = os.path.join(root, "modules", "v3_utils.py")
    v3_utils_constants = extract_constants(v3_utils_path)

    # 4. paper_trades.jsonl & risk_guard_state.json
    data_file_fields = []
    paper_trades = os.path.join(root, "data", "paper_trades.jsonl")
    if os.path.exists(paper_trades):
        try:
            line = open(paper_trades, "r").readline()
            if line:
                data = json.loads(line)
                data_file_fields.append({
                    "file": "data/paper_trades.jsonl",
                    "fields": list(data.keys())
                })
        except: pass
    else:
        # Default placeholder if not exists
        data_file_fields.append({
            "file": "data/paper_trades.jsonl",
            "fields": ["trade_id", "entry_time", "symbol", "direction", "pnl"]
        })
        
    risk_guard = os.path.join(root, "data", "risk_guard_state.json")
    if os.path.exists(risk_guard):
        try:
            data = json.load(open(risk_guard, "r"))
            data_file_fields.append({
                "file": "data/risk_guard_state.json",
                "fields": list(data.keys())
            })
        except: pass
    else:
        data_file_fields.append({
            "file": "data/risk_guard_state.json",
            "fields": ["daily_pnl", "trades_today", "consecutive_losses"]
        })

    # 5. strategy_components
    strategy_components = []
    mapper_path = os.path.join(root, "modules", "strategy_mapper.py")
    if os.path.exists(mapper_path):
        try:
            content = open(mapper_path, "r", encoding="utf-8").read()
            matches = re.finditer(r'[\'"](.*?)[\'"]\s*:\s*StrategyCandidate', content)
            for m in matches:
                strategy_components.append({
                    "strategy": m.group(1),
                    "min_confidence": 0,
                    "regimes": []
                })
        except: pass

    # 6. log_levels
    log_levels_observed = ["INFO", "WARNING", "ERROR", "DEBUG"]

    # 7. notification_types
    notification_types = [
        {"type": "trade_entry", "channel": "telegram"},
        {"type": "trade_exit", "channel": "telegram"},
        {"type": "riskguard_trip", "channel": "telegram"}
    ]

    # 8. subprocess
    subprocess_capabilities = [
        {"action": "start_live_trader", "command": "python live_options_trader.py"},
        {"action": "stop_live_trader", "command": "SIGTERM"},
        {"action": "run_backtest", "command": "python main_backtest.py --start ... --end ..."}
    ]

    inventory = {
        "phase": 1,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "api_endpoints": api_endpoints,
        "websocket_endpoints": ws_endpoints,
        "config_fields": config_fields,
        "v3_utils_constants": v3_utils_constants,
        "data_file_fields": data_file_fields,
        "strategy_components": strategy_components,
        "log_levels_observed": log_levels_observed,
        "notification_types": notification_types,
        "subprocess_capabilities": subprocess_capabilities
    }

    with open("backend_inventory_v1.json", "w") as f:
        json.dump(inventory, f, indent=2)
    print("backend_inventory_v1.json generated successfully")
    print(f"API Endpoints: {len(api_endpoints)}")
    print(f"Config Fields: {len(config_fields)}")
    print(f"Constants: {len(v3_utils_constants)}")

if __name__ == "__main__":
    main()
