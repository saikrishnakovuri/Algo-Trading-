import json

CONFIG_FILE = "meta_config.json"

def update_config(stocks, setups):
    """Saves the filtered list of profitable stocks and setups to a config file."""
    config = {
        "allowed_stocks": stocks,
        "allowed_setups": setups
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✅ Meta-config updated with {len(stocks)} stocks and {len(setups)} setups.")
