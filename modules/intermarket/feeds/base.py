from typing import Dict, Any, Optional
from datetime import datetime
try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

@runtime_checkable
class CrossAssetFeed(Protocol):
    """
    Protocol for cross-asset data feeds.
    """
    def get_latest_data(self, symbol: str) -> Dict[str, Any]:
        """
        Returns latest OHLCV and metadata for a symbol.
        Expected keys: 'close', 'open', 'high', 'low', 'volume', 'timestamp', 'session_return'
        """
        ...

    def get_history(self, symbol: str, interval: str, count: int) -> Any:
        """
        Returns historical data.
        """
        ...
