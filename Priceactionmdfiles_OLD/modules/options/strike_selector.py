import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import logging

logger = logging.getLogger("OptionSelector")

class OptionSelector:
    """
    Selects the optimal strike, expiry, and strategy (Buy/Spread) for a signal.
    
    Logic: ATM/OTM selection based on signal strength and time of day.
    Expiry management: Handles Wed/Thurs theta bomb by shifting to next week.
    Strategy shift: Switches to Credit Spreads if IV/VIX is too high.
    """
    
    def __init__(self, broker=None):
        self.broker = broker # Reserved for live API calls
        self.nifty_step = 50
        self.bn_step = 100
        
    def _get_atm_strike(self, price: float, symbol: str) -> int:
        step = self.bn_step if symbol == "BANKNIFTY" else self.nifty_step
        return int(round(price / step) * step)

    def _select_expiry_date(self, current_ts: datetime, expiry_list: list) -> str:
        """
        Logic for selecting the right weekly expiry.
        - If today is Thursday (expiry day), use NEXT week.
        - If today is Wednesday and after 13:00, use NEXT week.
        """
        current_date = current_ts.date()
        current_time = current_ts.time()
        
        # Sort expiries chronologically
        expiries = sorted([datetime.strptime(e, '%Y-%m-%d').date() for e in expiry_list])
        
        # Filter out past expiries
        valid_expiries = [e for e in expiries if e >= current_date]
        if not valid_expiries: return None
        
        nearest_expiry = valid_expiries[0]
        
        # Wednesday/Thursday Shift Logic
        is_expiry_day = (nearest_expiry == current_date)
        is_wednesday_afternoon = (current_date.weekday() == 2 and current_time >= time(13, 0))
        
        if is_expiry_day or is_wednesday_afternoon:
            # Shift to next week if available
            return valid_expiries[1].strftime('%Y-%m-%d') if len(valid_expiries) > 1 else nearest_expiry.strftime('%Y-%m-%d')
            
        return nearest_expiry.strftime('%Y-%m-%d')

    def select_option(self, 
                      signal_direction: str, 
                      signal_strength: int, 
                      spot_price: float, 
                      vix_level: float,
                      expiry_list: list,
                      option_chain: pd.DataFrame,
                      current_ts: datetime) -> dict:
        """
        Selects the exact option contract to trade.
        """
        symbol = "BANKNIFTY" if spot_price > 30000 else "NIFTY"
        current_time = current_ts.time()
        
        # 1. Determine Expiry
        expiry = self._select_expiry_date(current_ts, expiry_list)
        if not expiry: return None
        
        # 2. Determine Moneyness (Time-Based Enhancement)
        # Morning: 1-strike OTM allowed for leverage if signal is moderate.
        # Afternoon: Strictly ATM to combat theta.
        is_morning = current_time < time(11, 30)
        atm_strike = self._get_atm_strike(spot_price, symbol)
        
        strike_to_buy = atm_strike
        step = self.bn_step if symbol == "BANKNIFTY" else self.nifty_step
        
        if is_morning and signal_strength < 80:
            # Shift 1-strike OTM
            strike_to_buy = atm_strike + step if signal_direction == 'CE' else atm_strike - step
        
        # 3. Strategy Switch: Debit vs Credit (High IV Enhancement)
        # If VIX > 20, buying is expensive. Switch to a Credit Spread logic (placeholder for next phase)
        strategy_type = "NAKED_BUY"
        if vix_level > 20.0:
            strategy_type = "CREDIT_SPREAD" # Logic will be implemented in Phase 3
            # For now, we proceed with caution or skip
            logger.info(f"[{symbol}] High VIX {vix_level}. Strategy: {strategy_type}")

        # 4. Fetch Contract Data & Validate
        # Filter chain for selected expiry and strike
        contract = option_chain[(option_chain['expiry'] == expiry) & 
                                (option_chain['strike'] == strike_to_buy) & 
                                (option_chain['type'] == signal_direction)]
        
        if contract.empty:
            logger.warning(f"No contract found for {symbol} {expiry} {strike_to_buy} {signal_direction}")
            return None
            
        target_contract = contract.iloc[0]
        premium = target_contract['ltp']
        delta = target_contract.get('delta', 0.5)
        theta = target_contract.get('theta', 0.0)
        bid = target_contract.get('bid', premium)
        ask = target_contract.get('ask', premium)
        oi = target_contract.get('oi', 0)
        vol = target_contract.get('volume', 0)

        # --- 5. HARD VALIDATIONS ---
        # Premium Bounds
        if not (50 <= premium <= 450):
            logger.info(f"[{symbol}] Premium {premium} out of bounds (50-450).")
            return None
            
        # Liquidity Check (Spread < ₹4 for index options)
        spread = ask - bid
        if spread > 4.0:
            logger.info(f"[{symbol}] Wide Spread {spread} > 4. Skipping.")
            return None
            
        # OI & Volume Check
        if oi < 500000 or vol < 50000:
            logger.info(f"[{symbol}] Low Liquidity (OI: {oi}, Vol: {vol}). skipping.")
            return None
            
        # Delta Check
        if abs(delta) < 0.25:
            logger.info(f"[{symbol}] Low Delta {delta}. Option too far OTM.")
            return None

        # 6. Contract Specs
        lot_size = 30 if symbol == "BANKNIFTY" else 65 # User Specified
        
        # Lookup real token and tradingsymbol from ScripMaster
        from modules.options.scrip_master import scrip_master
        token = scrip_master.lookup_option(symbol, expiry, strike_to_buy, signal_direction)
        
        # If not found via components, try to construct likely Angel symbol for reverse lookup
        # Angel format is usually SYMBOL24MAY24050CE
        if not token:
            # Simple construction for logging/fallback
            real_symbol = f"{symbol}{datetime.strptime(expiry, '%Y-%m-%d').strftime('%y%b').upper()}{strike_to_buy}{signal_direction}"
            logger.warning(f"Token not found in ScripMaster for {symbol} {expiry} {strike_to_buy} {signal_direction}. Constructing: {real_symbol}")
        else:
            # We could do a reverse lookup to get the exact tradingsymbol string
            # For now, we'll store the token which is the most important part.
            real_symbol = f"{symbol}_{strike_to_buy}_{signal_direction}" # Keep internal format if needed
            
        return {
            'symbol': symbol,
            'strike': strike_to_buy,
            'option_type': signal_direction,
            'expiry': expiry,
            'premium': premium,
            'token': token,
            'tradingsymbol': real_symbol,
            'delta': delta,
            'theta': theta,
            'lot_size': lot_size,
            'bid': bid,
            'ask': ask,
            'strategy_type': strategy_type,
            'timestamp': current_ts
        }
