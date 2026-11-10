import os

files = [
    'modules/data_adapters/instrument_normalizer.py', 
    'modules/data_adapters/market_hours.py', 
    'AlgoTradingTelegramBotAndFrontend/backend/test_import.py',
    'modules/data_adapters/base_adapter.py', 
    'modules/data_adapters/__init__.py'
]

for f in files:
    try:
        with open(f, 'r') as file:
            content = file.read()
        
        # We need to un-escape the \" characters that were incorrectly added
        content = content.replace('\\"', '"')
        
        with open(f, 'w') as file:
            file.write(content)
        print(f'Fixed {f}')
    except Exception as e:
        print(f'Error fixing {f}: {e}')
