from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
from modules.intermarket.engine import IntermarketRelativeStrengthEngine
from modules.intermarket.schemas import IndexContext, UniverseSnapshot, CrossAssetSnapshot

class IntermarketAdapter:
    def __init__(self, config_path: str = "config/intermarket.yaml"):
        self.engine = IntermarketRelativeStrengthEngine(config_path)

    def build_index_context(self, symbol: str, df_5m: pd.DataFrame, df_15m: pd.DataFrame, regime: str) -> IndexContext:
        return IndexContext(
            symbol=symbol,
            ohlcv_5m=df_5m,
            ohlcv_15m=df_15m,
            session_open=df_5m['open'].iloc[0] if not df_5m.empty else 0.0,
            regime=regime
        )

    def build_universe_snapshot(self, all_stock_data: Dict[str, pd.DataFrame]) -> UniverseSnapshot:
        symbol_snapshots = {}
        for sym, df in all_stock_data.items():
            if not df.empty:
                last = df.iloc[-1]
                first = df.iloc[0]
                symbol_snapshots[sym] = {
                    'close': last['close'],
                    'open': first['open'],
                    'volume': last['volume'],
                    'vwap': (df['close'] * df['volume']).sum() / df['volume'].sum() if df['volume'].sum() > 0 else last['close']
                }
        return UniverseSnapshot(timestamp=datetime.now(), symbol_snapshots=symbol_snapshots)
