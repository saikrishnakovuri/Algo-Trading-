import pandas as pd
import numpy as np
import yaml
import logging
from datetime import datetime, time
from typing import Dict, Any, List, Optional
from modules.charting.aggregator import ChartDataAggregator
from modules.charting.structure_detector import StructureDetector

class StructureStrategyEngine:
    def __init__(self, config_path: str = "config/structure_strategy.yaml"):
        with open(config_path, "r", encoding='utf-8') as f:
            self.config = yaml.safe_load(f)["structure_strategy"]
        
        self.detector = StructureDetector()
        self.aggregator = ChartDataAggregator()
        self.structure_cache = {} # {symbol: {'structure': dict, 'last_update_idx': int}}
        
        self.logger = logging.getLogger("StructureStrategy")

    def generate_signal(self, df_5m: pd.DataFrame, symbol: str, 
                        df_15m: pd.DataFrame = None, config=None) -> Optional[Dict[str, Any]]:
        """Main signal generation — identifies entries based on chart structure."""
        if len(df_5m) < 50: return None # Need enough data for ATR and structure
        
        current_idx = len(df_5m) - 1
        current_price = df_5m['close'].iloc[-1]
        
        # 1. Time-of-Day Filter (09:30 - 15:15)
        curr_time = df_5m.index[-1].time()
        if curr_time < time(9, 30) or curr_time > time(15, 15):
            return None

        # 2. Get or update structure
        # REFINEMENT: Limit lookback to 500 bars (~7 days of 5m data) for speed and relevance
        lookback = 500
        df_detect = df_5m.iloc[-lookback:] if len(df_5m) > lookback else df_5m
        
        cache = self.structure_cache.get(symbol, {})
        refresh_interval = 30
        
        if not cache or (current_idx - cache.get('last_update_idx', -1) >= refresh_interval):
            structure = self.detector.detect_all(df_detect, symbol)
            # Add basic broken zone detection for Breakout Respect
            for z in structure['zones']:
                # If a candle closed through a resistance from below
                is_res = z['type'] in ['RESISTANCE', 'FLIP_ZONE']
                is_sup = z['type'] in ['SUPPORT', 'FLIP_ZONE']
                
                # Check recent history in detect slice
                z_df = df_detect
                broken_idx = -1
                for j in range(len(z_df)-1, max(0, len(z_df)-10), -1):
                    c = z_df.iloc[j]
                    if is_res and c['close'] > z['zone_high']: broken_idx = j; break
                    if is_sup and c['close'] < z['zone_low']: broken_idx = j; break
                
                if broken_idx != -1:
                    z['is_broken'] = True
                    z['broken_bars_ago'] = len(z_df) - 1 - broken_idx
            
            self.structure_cache[symbol] = {
                'structure': structure,
                'last_update_idx': current_idx
            }
        else:
            structure = cache['structure']

        # 3. Extract context
        curr_candle = df_5m.iloc[-1]
        atr = (df_5m['high'] - df_5m['low']).rolling(14).mean().iloc[-1]
        
        # Trend Alignment (50 SMA)
        sma_50 = df_5m['close'].rolling(50).mean().iloc[-1]
        trend = "UP" if current_price > sma_50 else "DOWN"

        potential_signals = []

        # --- A. Zone Bounce ---
        if self.config['signals']['zone_bounce']['enabled']:
            for z in structure['zones']:
                if z['touches'] < self.config['signals']['zone_bounce']['min_zone_touches']: continue
                
                # Zone Freshness check
                if (current_idx - z['last_touch_idx']) < 20: continue

                dist_pct = abs(current_price - z['price']) / z['price'] * 100
                if dist_pct <= self.config['signals']['zone_bounce']['max_distance_from_zone_pct']:
                    # Rejection check (Pin bar logic)
                    body = abs(curr_candle['close'] - curr_candle['open'])
                    wick_top = curr_candle['high'] - max(curr_candle['open'], curr_candle['close'])
                    wick_bot = min(curr_candle['open'], curr_candle['close']) - curr_candle['low']
                    
                    is_bull_rej = (wick_bot > 2 * body) and (z['type'] in ['SUPPORT', 'FLIP_ZONE'])
                    is_bear_rej = (wick_top > 2 * body) and (z['type'] in ['RESISTANCE', 'FLIP_ZONE'])
                    
                    if is_bull_rej or is_bear_rej:
                        # Volume Spike check (if enabled in config)
                        if self.config['signals']['zone_bounce']['require_volume_spike']:
                            vol_mean = df_5m['volume'].rolling(20).mean().iloc[-1]
                            if curr_candle['volume'] < vol_mean * 1.5: continue

                        direction = 'CE' if is_bull_rej else 'PE'
                        score = z['touches'] * 5 + 15
                        potential_signals.append({
                            'type': 'ZONE_BOUNCE', 'direction': direction, 'score': score, 
                            'level': z['price'], 'ref': z
                        })

        # --- B. FVG Fill ---
        if self.config['signals']['fvg_fill']['enabled']:
            for fvg in structure['fair_value_gaps']:
                if fvg['gap_size_pct'] < self.config['signals']['fvg_fill']['min_gap_size_pct']: continue
                if current_idx - fvg['origin_idx'] > self.config['signals']['fvg_fill']['max_age_bars']: continue
                
                if current_price >= fvg['zone_low'] and current_price <= fvg['zone_high']:
                    direction = 'CE' if fvg['type'] == 'BULLISH_FVG' else 'PE'
                    potential_signals.append({
                        'type': 'FVG_FILL', 'direction': direction, 'score': 55, 
                        'level': (fvg['zone_high'] + fvg['zone_low'])/2, 'ref': fvg
                    })

        # --- C. OB Retest ---
        if self.config['signals']['ob_retest']['enabled']:
            for ob in structure['order_blocks']:
                if current_price >= ob['zone_low'] and current_price <= ob['zone_high']:
                    direction = 'CE' if ob['type'] == 'BULLISH_OB' else 'PE'
                    potential_signals.append({
                        'type': 'OB_RETEST', 'direction': direction, 'score': 65, 
                        'level': (ob['zone_high'] + ob['zone_low'])/2, 'ref': ob
                    })

        if not potential_signals: return None
        
        # 4. Best Signal & Confluence
        best_sig = max(potential_signals, key=lambda x: x['score'])
        confidence = self.config['signals'][best_sig['type'].lower()]['confidence_base']
        reasons = [f"Signal: {best_sig['type']} at {best_sig['level']:.2f}"]
        confluences = []

        # Trend alignment penalty
        if trend == "UP" and best_sig['direction'] == "PE": confidence -= 25
        elif trend == "DOWN" and best_sig['direction'] == "CE": confidence -= 25

        # Breakout respect check
        for zone in structure['zones']:
            if zone.get('is_broken') and zone.get('broken_bars_ago', 999) < 10:
                breakout_dir = "UP" if current_price > zone['price'] else "DOWN"
                if breakout_dir == "UP" and best_sig['direction'] == "PE": return None
                if breakout_dir == "DOWN" and best_sig['direction'] == "CE": return None

        # Check overlaps
        for ob in structure['order_blocks']:
            if abs(ob['zone_low'] - best_sig['level']) / best_sig['level'] < 0.002:
                confidence += self.config['confluence']['zone_at_ob']
                confluences.append('ORDER_BLOCK')
        
        # Check VP POC
        vp = structure.get('volume_profile', {})
        if vp and abs(vp['poc'] - best_sig['level']) / best_sig['level'] < 0.002:
            confidence += self.config['confluence']['zone_at_vp_node']
            confluences.append('VP_POC')

        if confidence < self.config['entry']['min_confidence_pct']:
            return None

        # 5. Risk Management
        sl_buffer = current_price * (self.config['risk']['sl_buffer_pct'] / 100)
        if best_sig['direction'] == 'CE':
            sl = best_sig['level'] - sl_buffer
            nearest = self.detector.get_nearest_levels(current_price, structure)
            target = nearest['nearest_resistance']['price'] if nearest['nearest_resistance'] else current_price * 1.02
        else:
            sl = best_sig['level'] + sl_buffer
            nearest = self.detector.get_nearest_levels(current_price, structure)
            target = nearest['nearest_support']['price'] if nearest['nearest_support'] else current_price * 0.98

        # Anti-wick-out (0.7x ATR)
        min_sl_dist = atr * 0.7
        if abs(current_price - sl) < min_sl_dist:
            sl = current_price - min_sl_dist if best_sig['direction'] == 'CE' else current_price + min_sl_dist

        rr = abs(target - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0
        if rr < self.config['risk']['min_rr']:
            return None

        return {
            'signal': 'BUY' if best_sig['direction'] == 'CE' else 'SELL',
            'direction': best_sig['direction'],
            'entry': float(current_price),
            'sl': float(sl),
            'target1': float(target),
            'score': float(confidence / 10.0),
            'setup_type': best_sig['type'],
            'confidence': int(confidence),
            'confluence': confluences,
            'reasons': reasons + [f"Confluence: {', '.join(confluences)}", f"RR: {rr:.2f}", f"Trend: {trend}"]
        }
