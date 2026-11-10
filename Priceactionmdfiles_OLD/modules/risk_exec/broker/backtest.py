import uuid
from typing import List, Dict, Any

class BacktestAdapter:
    """
    Simulated broker for backtesting.
    """
    
    def __init__(self):
        self.orders = {}
        
    async def place_bracket_order(self, symbol: str, side: str, qty: int, 
                                  entry_price: float, sl_price: float, 
                                  targets: list) -> str:
        order_id = str(uuid.uuid4())
        self.orders[order_id] = {
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'entry': entry_price,
            'sl': sl_price,
            'targets': targets,
            'status': 'FILLED'
        }
        return order_id

    async def modify_sl(self, order_ref: str, new_sl: float) -> None:
        if order_ref in self.orders:
            self.orders[order_ref]['sl'] = new_sl

    async def close_position(self, order_ref: str, qty: int) -> dict:
        if order_ref in self.orders:
            # In a real backtest, the price would be current close
            return {'status': 'CLOSED', 'qty': qty}
        return {'status': 'NOT_FOUND'}
