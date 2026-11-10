import time
import logging
from datetime import datetime, timedelta, time as dtime
import pandas as pd
from modules.dashboard_bridge import bridge

logger = logging.getLogger("OptionTradeManager")

class OptionTradeManager:
    """
    Manages Option Trade execution and adaptive exit monitoring.
    """
    def __init__(self, broker, notifier=None, risk_manager=None):
        self.broker = broker
        self.notifier = notifier
        self.risk_manager = risk_manager
        self.risk_guard = None # Phase 21
        self.active_trades = {} # trade_id -> details

    def enter_trade(self, signal: dict, option_details: dict, capital: float, paper_mode: bool = True) -> str:
        """
        Executes a new option entry with positioning and timing logic.
        """
        symbol = signal['symbol']
        vix = signal['vix']
        spot_atr = signal.get('spot_atr', 50.0) 
        
        premium = option_details['premium']
        
        # --- ADAPTIVE SL CALCULATION ---
        adaptive = signal.get('adaptive_exits', {})
        sl_type = adaptive.get('sl_type', 'SL_ATR_1')
        tp_type = adaptive.get('tp_type', 'TP_TRAIL_ATR')
        
        if sl_type == 'SL_EMA20':
            # Distance from spot to EMA20 as SL proxy
            sl_dist = abs(signal['spot_price'] - signal.get('ema20', signal['spot_price']))
        elif sl_type == 'SL_ATR_2':
            sl_dist = spot_atr * 2.0
        else: # Default SL_ATR_1
            sl_dist = spot_atr * 1.0

        # Floor SL at 8 points premium to avoid noise stopouts
        if sl_dist < 8: sl_dist = 8 
        
        # Use Risk Manager for Position Sizing
        qty = self.risk_manager.get_position_size(symbol, premium, sl_dist)
        if qty <= 0:
            logger.warning(f"Sizing returned 0 for {symbol}. Skipping.")
            return None
        
        # --- ORDER PLACEMENT ---
        if not paper_mode:
            tradingsymbol = option_details.get('tradingsymbol', f"{symbol}_{option_details['strike']}_{option_details['option_type']}")
            token = option_details.get('token', "")
            order_id = self.broker.place_order(tradingsymbol, token, qty, "BUY", order_type="MARKET")
            if not order_id:
                logger.error(f"Order Placement Failed for {tradingsymbol}")
                return None
            logger.info(f"REAL ORDER PLACED: {order_id}")

        entry_price = premium 
        trade_id = f"TRD_{datetime.now().strftime('%H%M%S')}_{symbol}"
        
        self.active_trades[trade_id] = {
            'symbol': symbol,
            'strike': option_details['strike'],
            'type': option_details['option_type'],
            'expiry': option_details['expiry'],
            'token': option_details.get('token'),
            'tradingsymbol': option_details.get('tradingsymbol'),
            'entry_price': entry_price,
            'qty': qty,
            'initial_qty': qty,
            'start_time': datetime.now(),
            'sl_dist': sl_dist,
            'sl_price': entry_price - sl_dist,
            'max_premium_reached': entry_price,
            'partial_booked': False,
            'vix_at_entry': vix,
            'paper_mode': paper_mode,
            'sl_type': sl_type,
            'tp_type': tp_type,
            'context': adaptive.get('context', 'Unknown')
        }
        
        msg = f"[ENTRY] {'(PAPER) ' if paper_mode else ''}{symbol} | Context: {self.active_trades[trade_id]['context']} | SL Mode: {sl_type} | TP Mode: {tp_type} | Qty: {qty} | Entry: Rs {entry_price:.2f}"
        logger.info(msg)
        if self.notifier: self.notifier.send_message(msg)
        
        return trade_id

    def monitor_exits(self, live_quotes: dict):
        """
        Evaluates active trades against Adaptive Exit rules.
        """
        now = datetime.now()
        exited_ids = []
        
        for tid, t in self.active_trades.items():
            quote = live_quotes.get(tid)
            if not quote: continue
            
            curr_premium = quote['ltp']
            if curr_premium <= 0: continue
            
            tp_type = t['tp_type']
            
            # --- 1. EOD RULE (15:15 IST) ---
            if now.time() >= dtime(15, 15):
                self.close_trade(tid, curr_premium, "EOD_FORCE_CLOSE")
                exited_ids.append(tid); continue

            # --- 2. UPDATE TRAILING LOGIC BASED ON TP_TYPE ---
            if curr_premium > t['max_premium_reached']:
                t['max_premium_reached'] = curr_premium
                
                current_r = (curr_premium - t['entry_price']) / t['sl_dist']
                
                # A. FIX_2R TARGET
                if tp_type == 'TP_FIX_2R' and current_r >= 2.0:
                    self.close_trade(tid, curr_premium, "TARGET_2R_HIT")
                    exited_ids.append(tid); continue

                # B. PARTIAL_1R (Wait for 1.0R)
                elif tp_type == 'TP_PARTIAL_1R':
                    if current_r >= 1.0 and not t['partial_booked']:
                        partial_qty = t['qty'] // 2
                        if partial_qty > 0:
                            logger.info(f"[{t['symbol']}] T1 Hit (1.0R). Booking 50%.")
                            t['qty'] -= partial_qty
                            if self.risk_manager:
                                self.risk_manager.daily_pnl += (curr_premium - t['entry_price']) * partial_qty
                        t['partial_booked'] = True
                        t['sl_price'] = t['entry_price'] # Move to BE
                    
                    # Step trail after partial
                    if t['partial_booked']:
                        steps = int((current_r - 1.0) / 0.5)
                        if steps > 0:
                            new_sl = t['entry_price'] + (0.5 + steps * 0.5) * t['sl_dist']
                            t['sl_price'] = max(t['sl_price'], new_sl)

                # C. TRAIL_ATR (Dynamic Trailing)
                elif tp_type == 'TP_TRAIL_ATR':
                    new_sl = curr_premium - (1.5 * t['sl_dist'])
                    if new_sl > t['sl_price']:
                        t['sl_price'] = new_sl

            # --- 3. CHECK STOP LOSS ---
            if curr_premium <= t['sl_price']:
                reason = f"STOP_EXIT_{tp_type}"
                self.close_trade(tid, curr_premium, reason)
                exited_ids.append(tid); continue

        # Cleanup
        for tid in exited_ids:
            if tid in self.active_trades:
                del self.active_trades[tid]

    def close_trade(self, trade_id: str, exit_price: float, reason: str):
        """Executes the exit order and logs results."""
        t = self.active_trades[trade_id]
        pnl_points = exit_price - t['entry_price']
        total_pnl = pnl_points * t['qty']
        
        # --- REAL EXIT ORDER ---
        if not t.get('paper_mode', True):
            tradingsymbol = t.get('tradingsymbol', f"{t['symbol']}_{t['strike']}_{t['type']}")
            token = t.get('token', "")
            self.broker.place_order(tradingsymbol, token, t['qty'], "SELL", order_type="MARKET")
            logger.info(f"REAL EXIT ORDER PLACED for {tradingsymbol}")

        msg = f"EXIT: {t['symbol']} | Reason: {reason} | Exit: Rs {exit_price:.2f} | PnL: Rs {total_pnl:,.2f}"
        logger.info(msg)
        if self.notifier: self.notifier.send_message(msg)
        
        # Record risk
        if self.risk_manager:
            self.risk_manager.record_trade(total_pnl, datetime.now())
            
        if self.risk_guard:
            self.risk_guard.record_trade(total_pnl, datetime.now())

        # Push to Dashboard
        r_multiple = pnl_points / t['sl_dist'] if t['sl_dist'] > 0 else 0
        bridge.trade_close(trade_id, exit_price, reason, total_pnl, round(r_multiple, 2))

    def get_active_status(self):
        status_list = []
        for tid, t in self.active_trades.items():
            status_list.append({
                'id': tid,
                'sym': t['symbol'],
                'type': t['type'],
                'qty': t['qty'],
                'entry': t['entry_price'],
                'target': t.get('target_1', 0),
                'sl': t['sl_price'],
                'time': str(datetime.now() - t['start_time']).split('.')[0]
            })
        return status_list
