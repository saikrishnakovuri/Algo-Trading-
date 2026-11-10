import pandas as pd
import numpy as np
from datetime import time, datetime
import logging
import os

from modules.momentum_engine import MomentumBreakoutEngine

logger = logging.getLogger("OptionsSignalAdapter")

class IndexLiquidityTrapAdapter:
    """
    Adapts the MomentumBreakoutEngine to detect Liquidity Traps (Fakeout Fades)
    specifically for NIFTY and BANKNIFTY index options.
    
    Logic: Detects Momentum Breakout -> Fades it (Bulls trapped? Buy PE. Bears trapped? Buy CE).
    Enhancements: Psychological strike proximity, Delta OI confirmation, 
                 Dynamic Expiry Theta Gate, and VWAP Gravity.
    """
    
    def __init__(self):
        self.momentum_engine = MomentumBreakoutEngine()
        
    def _get_nearest_strike(self, price: float, symbol: str) -> int:
        """Calculate the nearest options strike based on index step size."""
        # Nifty: 50, BankNifty: 100
        step = 100 if symbol == "BANKNIFTY" else 50
        return int(round(price / step) * step)
        
    def _is_round_number_strike(self, strike: int, symbol: str) -> bool:
        """Check if the strike is a major psychological level."""
        if symbol == "BANKNIFTY" and strike % 500 == 0:
            return True
        if symbol == "NIFTY" and strike % 100 == 0:
            return True
        return False

    def evaluate_signal(self,
                        df_5m: pd.DataFrame,
                        symbol: str,                        vix_value: float, 
                        pcr_value: float, 
                        oi_data: dict, 
                        is_expiry_day: bool) -> dict:
        """
        Evaluate for Hybrid Signal: VWAP_BOUNCE or MOMENTUM_BREAKOUT.
        """
        if df_5m is None or len(df_5m) < 50:
            return None
            
        latest_ts = df_5m.index[-1]
        latest_time = latest_ts.time()
        
        # --- 1. TIME GATE FILTERS ---
        # if latest_time < time(9, 45):
        #     return None
        # cutoff_time = time(13, 0) if is_expiry_day else time(14, 0)
        # if latest_time >= cutoff_time:
        #     return None

        # Calculate required technicals dynamically
        df_today = df_5m[df_5m.index.date == latest_ts.date()].copy()
        if len(df_today) == 0: return None
        
        # VWAP calculation for the current session
        v = df_today['volume'].replace(0, 1)
        df_today['cum_vol'] = v.cumsum()
        df_today['cum_vol_price'] = (df_today['close'] * v).cumsum()
        df_today['VWAP'] = df_today['cum_vol_price'] / df_today['cum_vol']
        vwap = df_today['VWAP'].iloc[-1]
        
        # Trend & Volatility Indicators
        # df_5m is already lowercased by MasterStrategySelector
        if 'ema20' not in df_5m.columns:
            from modules.indicator_cache import precompute_indicators
            df_5m = precompute_indicators(df_5m)
        
        bar = df_5m.iloc[-1]
        prev_bar = df_5m.iloc[-2]
        c, o, h, l = bar['close'], bar['open'], bar['high'], bar['low']
        
        ema20 = bar['ema20']
        ema50 = bar['ema50']
        ema50_prev = prev_bar['ema50']
        trend = "RANGING"
        if c > ema50 * 1.005 and ema50 > ema50_prev: trend = "TRENDING_UP"
        elif c < ema50 * 0.995 and ema50 < ema50_prev: trend = "TRENDING_DOWN"
        
        vol_regime = "NORMAL_VOL"
        if bar['atr'] < 0.7 * bar['atr_avg']: vol_regime = "LOW_VOL"
        elif bar['atr'] > 1.3 * bar['atr_avg']: vol_regime = "HIGH_VOL"

        # --- 3. SETUP DETECTION (HYBRID) ---
        side = None
        setup_type = None
        
        # A. VWAP BOUNCE CHECK — Dip-and-Reclaim WITH Confluence (Phase 15)
        # Buffer ~0.05% of VWAP (~12 pts on NIFTY @ 24000)
        vwap_buffer = vwap * 0.0005
        prev_low   = prev_bar['low']
        prev_high  = prev_bar['high']

        ema20_val = bar['ema20']
        bar_range = max(h - l, 0.01)
        body_size = abs(c - o)
        body_pct  = body_size / bar_range

        vol_avg20 = df_5m['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = (bar['volume'] / vol_avg20) if vol_avg20 > 0 else 1.0

        # CE Long: dip-and-reclaim + above EMA20 + body dominant + volume OK
        if (prev_low <= vwap and 
            c > vwap + vwap_buffer and 
            l <= vwap + vwap_buffer and
            c > ema20_val and
            body_pct > 0.55 and
            vol_ratio > 0.75):
            side, setup_type = 'CE', 'VWAP_BOUNCE'

        # PE Short: mirror
        elif (prev_high >= vwap and 
              c < vwap - vwap_buffer and 
              h >= vwap - vwap_buffer and
              c < ema20_val and
              body_pct > 0.55 and
              vol_ratio > 0.75):
            side, setup_type = 'PE', 'VWAP_BOUNCE'
        
        # B. MOMENTUM BREAKOUT CHECK (If no VWAP bounce found)
        if not side:
            mom_signal = self.momentum_engine.generate_signal(df_5m, symbol, config={'range_atr_threshold': 3.5})
            if mom_signal and mom_signal['signal']:
                side = mom_signal['direction']
                setup_type = 'MOMENTUM_BREAKOUT'
        
        if not side: return None 
            
        # --- 4. FILTERS ---
        # Don't trade counter-trend breakouts
        if setup_type == 'MOMENTUM_BREAKOUT':
            if side == 'CE' and trend == 'TRENDING_DOWN': return None
            if side == 'PE' and trend == 'TRENDING_UP': return None
        
        # Graduated volatility handling
        vol_confidence_penalty = 0
        if vol_regime == "HIGH_VOL":
            # Only hard-veto true chaos (ATR > 1.8× avg)
            if bar['atr'] > 1.8 * bar['atr_avg']:
                logger.info(f"[{symbol}] VETO: ATR>1.8x avg (chaos).")
                return None
            vol_confidence_penalty = 10
            logger.info(f"[{symbol}] HIGH_VOL penalty applied: -10 confidence")

        # --- 5. ADAPTIVE EXIT ASSIGNMENT ---
        sl_type = 'SL_ATR_1'
        tp_type = 'TP_TRAIL_ATR'
        
        if setup_type == 'MOMENTUM_BREAKOUT':
            sl_type, tp_type = 'SL_ATR_1', 'TP_TRAIL_ATR'
        elif trend == "TRENDING_UP":
            sl_type, tp_type = 'SL_EMA20', 'TP_FIX_2R'
        
        base_confidence = 85 if setup_type == 'VWAP_BOUNCE' else 75
        final_confidence = max(40, base_confidence - vol_confidence_penalty)
        nearest_strike = self._get_nearest_strike(c, symbol)

        return {
            'strategy': setup_type,
            'symbol': symbol,
            'timestamp': latest_ts,
            'options_direction': side,
            'spot_price': c,
            'spot_atr': bar['atr'],
            'vwap': vwap,
            'trend': trend,
            'nearest_strike': nearest_strike,
            'confidence': final_confidence,
            'vix': vix_value,
            'pcr': pcr_value,
            'adaptive_exits': {
                'sl_type': sl_type,
                'tp_type': tp_type,
                'context': f"{trend} | {setup_type} | {vol_regime}"
            }
        }



    def get_technical_summary(self, df_5m: pd.DataFrame) -> dict:
        """Helper to get current technicals for logging without triggering a trade."""
        if df_5m is None or len(df_5m) < 2: return {}
        
        latest_ts = df_5m.index[-1]
        df_today = df_5m[df_5m.index.date == latest_ts.date()].copy()
        if len(df_today) == 0: return {}
        
        # VWAP with Proxy Volume
        v = df_today['volume'].replace(0, 1)
        df_today['cum_vol'] = v.cumsum()
        df_today['cum_vol_price'] = (df_today['close'] * v).cumsum()
        df_today['VWAP'] = df_today['cum_vol_price'] / df_today['cum_vol']
        
        # EMA
        ema50 = df_5m['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        
        return {
            'vwap': round(df_today['VWAP'].iloc[-1], 2),
            'ema50': round(ema50, 2),
            'spot': round(df_5m['close'].iloc[-1], 2)
        }
