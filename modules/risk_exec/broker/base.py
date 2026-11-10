from typing import Any
try:
    from typing_extensions import Protocol, runtime_checkable
except ImportError:
    # Minimal fallback if not available
    Protocol = object
    def runtime_checkable(cls): return cls

@runtime_checkable
class BrokerAdapter(Protocol):
    """
    Protocol defining the interface for all broker implementations.
    """
    async def place_bracket_order(self, symbol: str, side: str, qty: int, 
                                  entry_price: float, sl_price: float, 
                                  targets: list) -> str:
        """Places an entry order with SL and multiple TP targets."""
        ...

    async def modify_sl(self, order_ref: str, new_sl: float) -> None:
        """Modifies the stop loss level for an open position."""
        ...

    async def close_position(self, order_ref: str, qty: int) -> dict:
        """Closes part or all of a position at market."""
        ...
