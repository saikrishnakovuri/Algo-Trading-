import pandas as pd
import numpy as np

class MomentumBreakoutEngine:

    def detect_consolidation(self, df, lookback=20, config=None):
        """
        Find consolidation zones efficiently using rolling stats and limited scan.
        """
        atr_threshold = config.get('range_atr_threshold', 5.0) if config else 5.0
        min_consol_bars = config.get('consolidation_bars', 5) if config else 5
        
        # Calculate full series ATR for efficiency (Vectorized)
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
        atr_series = tr.rolling(14).mean()
        
        # Optimization: Only scan the last 100 bars for current breakout potential
        scan_start = max(lookback, len(df) - 100)
        
        consolidations = []
        consecutive_tight = 0
        start_idx = None

        # Faster windowed max/min using rolling
        rolling_high = df['high'].rolling(lookback).max()
        rolling_low = df['low'].rolling(lookback).min()
        
        for i in range(scan_start, len(df)):
            curr_atr = atr_series.iloc[i-1]
            if pd.isna(curr_atr) or curr_atr == 0: continue
                
            range_val = rolling_high.iloc[i-1] - rolling_low.iloc[i-1]
            range_ratio = range_val / curr_atr
            
            if range_ratio < atr_threshold: 
                if consecutive_tight == 0:
                    start_idx = i - lookback
                consecutive_tight += 1
            else:
                if consecutive_tight >= min_consol_bars: 
                    consolidations.append({
                        'high': df.iloc[start_idx:i]['high'].max(),
                        'low': df.iloc[start_idx:i]['low'].min(),
                        'bars': consecutive_tight,
                        'volume_avg': df.iloc[start_idx:i]['volume'].mean(),
                        'start_idx': start_idx,
                        'end_idx': i - 1
                    })
                consecutive_tight = 0
                start_idx = None
        
        if consecutive_tight >= min_consol_bars:
            consolidations.append({
                'high': df.iloc[start_idx:]['high'].max(),
                'low': df.iloc[start_idx:]['low'].min(),
                'bars': consecutive_tight,
                'volume_avg': df.iloc[start_idx:]['volume'].mean(),
                'start_idx': start_idx,
                'end_idx': len(df) - 1
            })
        return consolidations

    def detect_breakout(self, df, consolidations, current_idx, mtf_zones=None, config=None):
        """
        Check if current bar is a breakout from any recent consolidation.
        """
        participation_mode = bool(config.get('participation_mode', False)) if config else False
        vol_breakout_ratio = config.get('volume_breakout_ratio', 1.3) if config else 1.3
        body_impulse_ratio = config.get('body_impulse_ratio', 1.2) if config else 1.2
        use_slope_confirmation = bool(config.get('use_slope_confirmation', False)) if config else False
        min_slope_points = config.get('min_slope_points', 0.0) if config else 0.0
        
        current = df.iloc[current_idx]
        body = abs(current['close'] - current['open'])
        
        prev_5 = df.iloc[max(0, current_idx-5):current_idx]
        avg_body = (prev_5['close'] - prev_5['open']).abs().mean() if not prev_5.empty else body
        body_ratio = body / avg_body if avg_body > 0 else 0
        
        last_3 = df.iloc[max(0, current_idx-3):current_idx+1]
        bullish_count = sum(1 for _, r in last_3.iterrows() if r['close'] > r['open'])
        close_slope = current['close'] - df.iloc[max(0, current_idx-3)]['close']
        bullish_momentum = close_slope > min_slope_points if use_slope_confirmation else bullish_count >= 2
        bearish_momentum = close_slope < -min_slope_points if use_slope_confirmation else (len(last_3) - bullish_count) >= 2
        
        for consol in consolidations:
            if current_idx - consol['end_idx'] > 50:
                continue
            
            vol_ratio = current['volume'] / consol['volume_avg'] if consol['volume_avg'] > 0 else 0
            
            # LONG BREAKOUT
            if (current['close'] > consol['high'] and body_ratio > body_impulse_ratio and vol_ratio > vol_breakout_ratio and bullish_momentum):
                score = self._calculate_breakout_score(consol, vol_ratio, body_ratio, 'LONG', df, current_idx)
                if participation_mode:
                    score = self._scale_participation_score(score, vol_ratio, body_ratio, close_slope)
                return {
                    'signal': 'LONG',
                    'setup_type': 'PARTICIPATION_BREAKOUT' if participation_mode else 'MOMENTUM_BREAKOUT',
                    'breakout_level': consol['high'],
                    'consolidation': consol, 'volume_ratio': vol_ratio, 'body_ratio': body_ratio,
                    'score': score, 'entry': current['close'], 'sl': consol['low'], 'direction': 'CE',
                    'participation_mode': participation_mode, 'slope': close_slope
                }
            
            # SHORT BREAKOUT
            if (current['close'] < consol['low'] and body_ratio > body_impulse_ratio and vol_ratio > vol_breakout_ratio and bearish_momentum):
                score = self._calculate_breakout_score(consol, vol_ratio, body_ratio, 'SHORT', df, current_idx)
                if participation_mode:
                    score = self._scale_participation_score(score, vol_ratio, body_ratio, abs(close_slope))
                return {
                    'signal': 'SHORT',
                    'setup_type': 'PARTICIPATION_BREAKOUT' if participation_mode else 'MOMENTUM_BREAKOUT',
                    'breakout_level': consol['low'],
                    'consolidation': consol, 'volume_ratio': vol_ratio, 'body_ratio': body_ratio,
                    'score': score, 'entry': current['close'], 'sl': consol['high'], 'direction': 'PE',
                    'participation_mode': participation_mode, 'slope': close_slope
                }
        
        return {'signal': None}

    def _scale_participation_score(self, score, vol_ratio, body_ratio, slope):
        """
        Participation mode keeps weaker breakouts alive but scores them lower
        instead of treating every missing strict confirmation as a hard reject.
        """
        scaled = score
        if vol_ratio < 1.3:
            scaled -= 0.7
        if body_ratio < 1.2:
            scaled -= 0.6
        if slope <= 0:
            scaled -= 0.5
        return round(max(3.0, scaled), 2)

    def _calculate_breakout_score(self, consol, vol_ratio, body_ratio, direction, df, idx):
        score = 0.0
        if vol_ratio > 2.0: score += 2.0
        elif vol_ratio > 1.5: score += 1.5
        else: score += 1.0

        bars = consol['bars']
        if bars >= 20: score += 2.0
        elif bars >= 15: score += 1.5
        else: score += 1.0

        if body_ratio > 2.0: score += 1.5
        elif body_ratio > 1.5: score += 1.0
        else: score += 0.5

        if idx >= 20:
            sma_20 = df.iloc[idx-20:idx]['close'].mean()
            current_close = df.iloc[idx]['close']
            if direction == 'LONG' and current_close > sma_20: score += 1.5
            elif direction == 'SHORT' and current_close < sma_20: score += 1.5

        current_bar_range = abs(df.iloc[idx]['high'] - df.iloc[idx]['low'])
        consol_range = consol['high'] - consol['low']
        if current_bar_range > 0:
            tightness = consol_range / current_bar_range
            if tightness < 1.0: score += 1.0
            elif tightness < 1.5: score += 0.5
        return round(score, 2)

    def detect_ema_crossover(self, df, current_idx, vwap=None):
        """
        Detects EMA 9/21 crossover with VWAP confirmation.
        Only valid in TRENDING regimes.
        """
        if current_idx < 25: return {'signal': None}
        
        # Calculate EMAs
        ema9 = df['close'].ewm(span=9, adjust=False).mean()
        ema21 = df['close'].ewm(span=21, adjust=False).mean()
        
        curr_9, curr_21 = ema9.iloc[current_idx], ema21.iloc[current_idx]
        prev_9, prev_21 = ema9.iloc[current_idx-1], ema21.iloc[current_idx-1]
        
        curr_price = df['close'].iloc[current_idx]
        
        # BULLISH CROSSOVER
        if prev_9 <= prev_21 and curr_9 > curr_21:
            if vwap is None or curr_price > vwap:
                vol_ratio = df['volume'].iloc[current_idx] / df['volume'].rolling(20).mean().iloc[current_idx]
                score = 5.0 + min(5.0, (curr_9 - curr_21) / (curr_price * 0.001) + (vol_ratio - 1.0) * 2)
                return {
                    'signal': 'LONG', 'setup_type': 'EMA_CROSSOVER', 'score': round(score, 2),
                    'entry': curr_price, 'sl': curr_21, 'direction': 'CE'
                }
        
        # BEARISH CROSSOVER
        if prev_9 >= prev_21 and curr_9 < curr_21:
            if vwap is None or curr_price < vwap:
                vol_ratio = df['volume'].iloc[current_idx] / df['volume'].rolling(20).mean().iloc[current_idx]
                score = 5.0 + min(5.0, (curr_21 - curr_9) / (curr_price * 0.001) + (vol_ratio - 1.0) * 2)
                return {
                    'signal': 'SHORT', 'setup_type': 'EMA_CROSSOVER', 'score': round(score, 2),
                    'entry': curr_price, 'sl': curr_21, 'direction': 'PE'
                }
        
        return {'signal': None}

    def generate_signal(self, df, symbol, config=None):
        if len(df) < 30:
            return {'signal': None}
        
        consolidations = self.detect_consolidation(df, config=config)
        if not consolidations:
            return {'signal': None}
        
        current_idx = len(df) - 1
        breakout = self.detect_breakout(df, consolidations, current_idx, config=config)
        
        if breakout['signal'] is None:
            return {'signal': None}
        
        entry = breakout['entry']
        sl = breakout['sl']
        dist = abs(entry - sl)
        target_r = config.get('target_r', 1.5) if config else 1.5
        
        target1 = entry + target_r * dist if breakout['direction'] == 'CE' else entry - target_r * dist
        target2 = entry + (target_r * 2) * dist if breakout['direction'] == 'CE' else entry - (target_r * 2) * dist
        
        return {
            'signal': 'BUY' if breakout['signal'] == 'LONG' else 'SELL',
            'setup_type': breakout.get('setup_type', 'MOMENTUM_BREAKOUT'),
            'entry': float(entry), 'sl': float(sl), 'target1': float(target1), 'target2': float(target2),
            'score': breakout['score'], 'checklist_score': breakout['score'],
            'confidence': min(95, max(45, breakout['score'] * 10)),
            'direction': breakout['direction'], 'type': breakout['direction'],
            'volume_ratio': breakout['volume_ratio'], 'body_ratio': breakout['body_ratio'],
            'participation_mode': breakout.get('participation_mode', False),
            'slope': breakout.get('slope'),
            'consolidation_bars': breakout['consolidation']['bars'],
            'reasons': [
                f"Breakout {breakout['signal']} above consolidation",
                f"Volume: {breakout['volume_ratio']:.1f}x avg",
                f"Consolidation: {breakout['consolidation']['bars']} bars"
            ]
        }

    @staticmethod
    def calculate_atr(df, period=14):
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def analyze_timeframes(self, mtf_data):
        """Helper to prepare analysis for momentum-based signals."""
        return {
            '15m': mtf_data.get('15m'),
            '5m': mtf_data.get('5m'),
            '1m': mtf_data.get('1m')
        }
