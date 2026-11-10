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

def get_hashes():
    hashes = []
    for fp in LOCKED:
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
                hashes.append(f"{h}  {fp}")
        else:
            print(f"Warning: {fp} not found")
    return hashes

if __name__ == "__main__":
    hashes = get_hashes()
    with open("LAUNCH_HASHES_PRE.txt", "w") as f:
        f.write("\n".join(hashes) + "\n")
    for h in hashes:
        print(h)
