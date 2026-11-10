import yaml
import os

# Load Centralized Configs (Phase 25a compliance)
def load_yaml(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return {}

CAPITAL_CFG = load_yaml('config/capital.yaml').get('capital', {})
INSTRUMENT_CFG = load_yaml('config/instrument_master.yaml').get('lot_sizes', {})

TOTAL_CAPITAL = float(CAPITAL_CFG.get('starting', 500000.0))
NIFTY_LOT_SIZE = int(INSTRUMENT_CFG.get('NIFTY', 65))
BANKNIFTY_LOT_SIZE = int(INSTRUMENT_CFG.get('BANKNIFTY', 30))
FINNIFTY_LOT_SIZE = int(INSTRUMENT_CFG.get('FINNIFTY', 40))

MAX_RISK_PCT_EQUITY = CAPITAL_CFG.get('per_trade_risk_pct', 1.0) / 100.0
MAX_RISK_PCT_OPTIONS = MAX_RISK_PCT_EQUITY * 2.0  # Conservative multiplier

DAILY_LOSS_LIMIT_PCT = CAPITAL_CFG.get('daily_loss_pct', 4.0) / 100.0
WEEKLY_LOSS_LIMIT_PCT = CAPITAL_CFG.get('weekly_loss_pct', 8.0) / 100.0
MAX_LEVERAGE = 5
NO_ENTRY_AFTER = "12:00"
FORCE_CLOSE_AT = "15:15"
MARKET_OPEN = "09:15"
SIGNAL_GATE = "10:00"
COOLDOWN_AFTER_2_LOSSES_MIN = 60
BROKERAGE_EQUITY = 87           # ₹ per round trip
BROKERAGE_OPTIONS = 70          # ₹ avg per round trip
DASHBOARD_URL = "http://localhost:8000"  # backend URL for bridge

NO_TRADE_ZONES = ["RANGING", "HIGH_VOL", "VWAP_PUSH", "EMA_BOUNCE"]
REGIME_TYPES = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "CHOPPY"]
ENTRY_STRATEGIES = ["VWAP_BOUNCE", "MOMENTUM_FOLLOW", "LIQUIDITY_TRAP",
                    "MOMENTUM_BREAKOUT", "MEAN_REVERSION", "EMA_CROSSOVER",
                    "BREAKOUT_RETEST"]
SL_TYPES = ["EMA20", "EMA50", "ATR_1", "ATR_2", "CANDLE", "SWING", "FIXED_1PCT"]
TP_TYPES = ["FIX_1.5R", "FIX_2R", "FIB_1.618R", "SR", "PARTIAL_1R",
            "PARTIAL_1.5R", "TRAIL_ATR"]
STOCK_UNIVERSE = {
    "NIFTY50": ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "INFY",
                "TCS", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"],
    "MIDCAP": ["ADANIENT", "BAJFINANCE", "TATAMOTORS", "WIPRO", "HCLTECH"]
}
