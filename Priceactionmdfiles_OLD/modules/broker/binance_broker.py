import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('live_trader')

class BinancePaperBroker:
    """
    Simulation broker for Binance Crypto paper trading.
    Supports fractional quantities and tracks USD balance.
    """
    def __init__(self, initial_balance=10000.0, state_file="data/binance_paper_state.json"):
        self.state_file = state_file
        self.load_state(initial_balance)

    def load_state(self, initial_balance):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.balance = state.get('balance', initial_balance)
                    self.positions = state.get('positions', {}) # symbol -> {qty, entry, side}
                    self.history = state.get('history', [])
                    return
            except:
                pass
        
        self.balance = initial_balance
        self.positions = {}
        self.history = []

    def save_state(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump({
                'balance': self.balance,
                'positions': self.positions,
                'history': self.history
            }, f, indent=2)

    def place_order(self, symbol, side, qty, price, order_type="MARKET"):
        """Simulates an order fill."""
        cost = qty * price
        
        if side == 'BUY':
            if cost > self.balance:
                logger.error(f"INSUFFICIENT FUNDS for {symbol}: Need {cost}, Have {self.balance}")
                return None
            self.balance -= cost
            self.positions[symbol] = {
                'qty': self.positions.get(symbol, {}).get('qty', 0) + qty,
                'entry': price,
                'side': 'LONG'
            }
        else: # SELL
            pos = self.positions.get(symbol)
            if not pos or pos['qty'] < qty:
                logger.error(f"NO POSITION to sell for {symbol}")
                return None
            self.balance += cost
            pos['qty'] -= qty
            if pos['qty'] <= 0.00001:
                del self.positions[symbol]

        order_id = f"sim_{int(datetime.now().timestamp() * 1000)}"
        self.history.append({
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'price': price,
            'time': datetime.now().isoformat()
        })
        self.save_state()
        return order_id

    def get_position(self, symbol):
        return self.positions.get(symbol)

    def get_balance(self):
        return self.balance
