import hashlib
import os

LOCKED = [
    "live_options_trader.py",
    "main_backtest.py",
    "modules/strategy_mapper.py",
    "modules/strategy_selector.py",
    "modules/v3_utils.py",
    "modules/candlestick_engine.py",
    "modules/risk_guard.py",
    "modules/regime/classifier.py",
    "modules/confidence_scorer.py",
    "modules/mean_reversion_engine.py",
    "modules/momentum_engine.py",
    "modules/context_detector.py",
    "modules/indicator_engine.py",
]

def verify_locked_files(reference_file="LAUNCH_HASHES_PRE.txt"):
    if not os.path.exists(reference_file):
        return False, "Reference hash file not found"
    
    with open(reference_file, 'r') as f:
        ref_lines = f.readlines()
    
    ref_hashes = {}
    for line in ref_lines:
        parts = line.strip().split('  ')
        if len(parts) == 2:
            ref_hashes[parts[1]] = parts[0]
            
    errors = []
    for fp in LOCKED:
        if not os.path.exists(fp):
            errors.append(f"Missing file: {fp}")
            continue
            
        with open(fp, 'rb') as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
            
        if fp not in ref_hashes:
            errors.append(f"No reference hash for: {fp}")
        elif current_hash != ref_hashes[fp]:
            errors.append(f"Hash mismatch for: {fp}")
            
    if errors:
        return False, errors
    return True, "All locked files verified"

def get_current_hashes():
    hashes = {}
    for fp in LOCKED:
        if os.path.exists(fp):
            with open(fp, 'rb') as f:
                hashes[fp] = hashlib.md5(f.read()).hexdigest()
    return hashes
