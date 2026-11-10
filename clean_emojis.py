
import re

def clean_file(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Remove all characters with code > 127
    clean_content = "".join(i for i in content if ord(i) < 128)
    
    with open(path, 'w', encoding='ascii') as f:
        f.write(clean_content)
    print(f"Cleaned {path}")

clean_file('backtest_engine.py')
clean_file('modules/price_action_engine.py')
clean_file('run_backtest.py')
