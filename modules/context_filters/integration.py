import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from modules.context_filters.stack import ContextFilterStack
from modules.context_filters.calendar import TradingCalendar
from modules.context_filters.schemas import AllowDecision

class ContextFilterAdapter:
    """
    Adapter to plug ContextFilterStack into PriceActionEngine.
    """
    
    def __init__(self, config_path: str = "config/context_filters.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.calendar = TradingCalendar(Path(self.config['calendar']['yaml_path']))
        self.stack = ContextFilterStack(self.config, self.calendar, Path(self.config['gap']['stats_path']))
        
    def evaluate_context(self, symbol: str, signal: Dict[str, Any], 
                         mtf_analyses: Dict[str, Any], regime: str, 
                         prior_ohlc: Dict[str, float], backtest_mode: bool = False) -> AllowDecision:
        
        df_5m = mtf_analyses.get('5m')
        df_1m = mtf_analyses.get('1m')
        
        from modules.price_action_engine import PriceActionEngine
        atr_5m = PriceActionEngine.calculate_atr(df_5m)
        
        # Approximate daily ATR if not provided
        atr_daily = atr_5m * 5.0 # Rough proxy
        
        # Today Open
        today_open = float(df_1m['open'].iloc[0]) if not df_1m.empty else 0.0
        prior_close = prior_ohlc.get('close', today_open)
        
        # Retracement Pct
        current_price = float(df_1m['close'].iloc[-1])
        gap_val = today_open - prior_close
        retracement_pct = (today_open - current_price) / gap_val if abs(gap_val) > 0 else 0.0
        
        # SMC Sweep (from signal metadata)
        sweep = False
        if 'smc_metadata' in signal:
            meta = signal['smc_metadata']
            # Search for sweep keywords in the aligned footprints strings
            sweep_keywords = ["Sweep", "PDH", "PDL", "SH", "SL", "EQH", "EQL"]
            sweep = any(any(kw in footprint for kw in sweep_keywords) for footprint in meta.aligned_footprints)

        now_ist = datetime.now() # In backtest this should be current row timestamp
        # Fix for backtest: use index of last row
        if not df_1m.empty:
            last_ts = df_1m.index[-1]
            if getattr(last_ts, 'tz', None) is not None:
                now_ist = last_ts.tz_convert('Asia/Kolkata').tz_localize(None)
            else:
                # Already naive and in IST
                now_ist = last_ts
        
        return self.stack.evaluate(
            symbol=symbol,
            signal_direction="LONG" if signal['trade'] == 'CE' else "SHORT",
            signal_type=signal.get('setup', 'OTHER'),
            now_ist=now_ist,
            ohlcv_5m=df_5m,
            ohlcv_1m=df_1m,
            prior_close=prior_close,
            today_open=today_open,
            atr_14_5m=atr_5m,
            atr_14_daily=atr_daily,
            regime=regime,
            sweep_at_gap_level=sweep,
            retracement_pct=retracement_pct,
            backtest_mode=backtest_mode
        )
