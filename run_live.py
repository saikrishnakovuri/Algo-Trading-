#!/usr/bin/env python3
"""
UNIFIED LIVE TRADING ENTRY POINT
Loads authoritative configuration and starts the live trading loop.
"""
import yaml
import json
import time
from datetime import datetime
from modules.broker_layer import AngelOneBroker
from live_trader_v1 import live_trader

def load_master_config():
    configs = {}
    config_files = [
        "config/regime.yaml",
        "config/vp_avwap.yaml",
        "config/smc.yaml",
        "config/context_filters.yaml",
        "config/risk_execution.yaml",
        "config/universe.yaml",
        "config/strategy_filter.yaml",
        "config/paper_mode.yaml",
    ]
    for f in config_files:
        try:
            with open(f, encoding="utf-8") as fh:
                key = f.split("/")[-1].replace(".yaml", "")
                configs[key] = yaml.safe_load(fh)
        except Exception as e:
            print(f"WARNING: Could not load {f}: {e}")
    return configs

def print_startup_banner(config, broker_status):
    is_paper = config.get('paper_mode', {}).get('mode') == 'PAPER'
    sf = config.get('strategy_filter', {}).get('strategies', {})
    
    print("=" * 60)
    print("🚀 ALGO TRADING SYSTEM - STARTUP SEQUENCE")
    print("=" * 60)
    print(f"  TIME     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  MODE     : {'🔴 PAPER TRADING (SIMULATED)' if is_paper else '🟢 LIVE TRADING (REAL MONEY)'}")
    print(f"  BROKER   : {'CONNECTED' if broker_status else 'FAILED'}")
    print(f"  LIMITS   : 3 API calls/sec (with retry backoff)")
    
    print("-" * 60)
    print("  ACTIVE STRATEGIES:")
    for strat, cfg in sf.items():
        if cfg.get('enabled'):
            scope = cfg.get('allowed_symbols', 'ALL')
            print(f"    - {strat:<18} | Scope: {str(scope)[:30]}")
            
    print("-" * 60)
    print("  MONITORING UNIVERSE:")
    universe = config.get('universe', {}).get('universe', {}).get('mappings', {})
    print(f"    Symbols: {', '.join(list(universe.keys())[:10])}...")
    print("=" * 60)

def main():
    # 1. Load authoritative config
    config = load_master_config()
    
    # 2. Verify Broker Connection & Tokens
    broker = AngelOneBroker()
    connected = broker.login()
    
    # 3. Print Banner
    print_startup_banner(config, connected)
    
    if not connected:
        print("FATAL: Broker connection failed. Aborting startup.")
        return

    # 4. Start Live Loop (Passing the config)
    # Note: live_trader_v1.py should be modified to accept this config
    # For now, we call it normally as it loads its own but uses the same modules.
    try:
        live_trader()
    except KeyboardInterrupt:
        print("\n👋 Shutdown signal received. Closing session...")

if __name__ == "__main__":
    main()
