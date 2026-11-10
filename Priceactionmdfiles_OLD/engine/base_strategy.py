"""
Abstract Base Strategy — every price action strategy extends this.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd
try:
    from .signal import Signal, SignalType, MarketBias
except ImportError:
    from signal import Signal, SignalType, MarketBias


class BaseStrategy(ABC):
    """
    All strategies MUST implement:
      - name (property)
      - category (property)
      - detect(df, timeframe) -> List[Signal]
    
    Optional overrides:
      - required_candles -> minimum candles needed
      - supported_timeframes -> list of valid timeframes
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """One of: 'advanced_concept', 'candlestick', 'price_action_pattern', 'support_resistance'"""
        pass

    @property
    def required_candles(self) -> int:
        """Minimum number of candles needed for detection. Override per strategy."""
        return 50

    @property
    def supported_timeframes(self) -> List[str]:
        """Timeframes this strategy works on. Override if restricted."""
        return ["1m", "5m", "15m", "1h", "4h", "1d"]

    @abstractmethod
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        """
        Core detection method.
        
        Args:
            df: OHLCV DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
                Index should be datetime. Most recent candle is LAST row.
            timeframe: Current chart timeframe string.
        
        Returns:
            List of Signal objects detected in the data.
            Return empty list if no pattern/signal found.
        """
        pass

    def validate_dataframe(self, df: pd.DataFrame) -> bool:
        """Check that DataFrame has required columns and enough data."""
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(set(df.columns)):
            return False
        if len(df) < self.required_candles:
            return False
        return True
