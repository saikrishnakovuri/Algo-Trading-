import os
import yaml
import re

def set_baseline(disabled=True):
    # 1. backtest_engine.py: Afternoon CE and Momentum filters
    with open('backtest_engine.py', 'r', encoding='ascii') as f:
        content = f.read()
    
    if disabled:
        # Disable filters
        content = re.sub(r'if trade_type == "CE" and entry_time >= dtime\(11, 30\):', 'if False: # trade_type == "CE" and entry_time >= dtime(11, 30):', content)
        content = re.sub(r'if not momentum_ok:', 'if False: # not momentum_ok:', content)
    else:
        # Enable filters
        content = re.sub(r'if False: # trade_type == "CE" and entry_time >= dtime\(11, 30\):', 'if trade_type == "CE" and entry_time >= dtime(11, 30):', content)
        content = re.sub(r'if False: # not momentum_ok:', 'if not momentum_ok:', content)
        
    with open('backtest_engine.py', 'w', encoding='ascii') as f:
        f.write(content)

    # 2. modules/price_action_engine.py: Zone respect filter
    with open('modules/price_action_engine.py', 'r', encoding='ascii') as f:
        content = f.read()
        
    if disabled:
        content = re.sub(r'if zone_respect < 0.50:', 'if False: # zone_respect < 0.50:', content)
    else:
        content = re.sub(r'if False: # zone_respect < 0.50:', 'if zone_respect < 0.50:', content)
        
    with open('modules/price_action_engine.py', 'w', encoding='ascii') as f:
        f.write(content)

    # 3. modules/intermarket/index_alignment.py: Nifty penalty
    with open('modules/intermarket/index_alignment.py', 'r', encoding='ascii') as f:
        content = f.read()
        
    if disabled:
        # Neutralize deltas
        content = re.sub(r'score_delta = [\d\.\-]+', 'score_delta = 0.0', content)
    else:
        # Restore deltas
        content = re.sub(r'alignment == "ALIGNED":\s+score_delta = 0.0', 'alignment == "ALIGNED":\s+score_delta = 0.5', content)
        content = re.sub(r'alignment == "CONTRA":\s+score_delta = 0.0', 'alignment == "CONTRA":\s+score_delta = -0.5', content)
        
    with open('modules/intermarket/index_alignment.py', 'w', encoding='ascii') as f:
        f.write(content)

    # 4. config/strategy_filter.yaml
    if disabled:
        with open('config/strategy_filter.yaml', 'r') as f:
            sf = yaml.safe_load(f)
        
        for strat in sf['strategies']:
            sf['strategies'][strat]['enabled'] = True
            sf['strategies'][strat]['allowed_symbols'] = 'ALL'
            sf['strategies'][strat]['min_score_override'] = 0.0
            
        with open('config/strategy_filter.yaml', 'w') as f:
            yaml.dump(sf, f)

def set_target(r_multiple):
    with open('modules/price_action_engine.py', 'r', encoding='ascii') as f:
        content = f.read()
    
    # Replace target1 = entry +/- X * dist
    content = re.sub(r"out\['target1'\] = entry \+ [\d\.]+ \* dist", f"out['target1'] = entry + {r_multiple} * dist", content)
    content = re.sub(r"out\['target1'\] = entry - [\d\.]+ \* dist", f"out['target1'] = entry - {r_multiple} * dist", content)
    
    with open('modules/price_action_engine.py', 'w', encoding='ascii') as f:
        f.write(content)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "disable": set_baseline(True)
        elif cmd == "enable": set_baseline(False)
        elif cmd == "target": set_target(float(sys.argv[2]))
