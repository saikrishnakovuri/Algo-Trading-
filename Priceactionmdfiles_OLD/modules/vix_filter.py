import pandas as pd
import yaml
import os

class VIXDirectionalFilter:
    """
    Uses India VIX 5m candle momentum to bias trade direction.
    VIX rising -> favor PE (shorts), penalize CE (longs)
    VIX falling -> favor CE (longs), penalize PE (shorts)
    
    # REVERT: To disable this filter entirely, set enabled=False in config
    #         or comment out the call in live_trader_v3.py
    """
    
    def __init__(self, config_path="config/vix_filter.yaml"):
        self.enabled = True
        self.vix_data = None
        self.last_vix_close = None
        self.vix_direction = "NEUTRAL"  # "RISING", "FALLING", "NEUTRAL", "SPIKE"
        self.config = {}
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)
                self.config = full_config.get('vix_filter', {})
                self.enabled = self.config.get('enabled', True)
        else:
            # Default fallback if config missing
            self.config = {
                'spike_threshold_pct': 3.0,
                'spike_3bar_threshold_pct': 5.0,
                'rising_threshold_pct': 0.5,
                'rising_3bar_threshold_pct': 1.5,
                'falling_threshold_pct': -0.5,
                'falling_3bar_threshold_pct': -1.5,
                'spike_long_block': True,
                'spike_short_boost': 15,
                'rising_long_penalty': 15,
                'rising_short_boost': 10,
                'falling_long_boost': 10,
                'falling_short_penalty': 15
            }

    def update(self, df_vix_5m: pd.DataFrame):
        """
        Call this ONCE per scan cycle with latest VIX 5m data.
        Uses the LAST CLOSED candle only (iloc[-1] in this historical/pre-sliced context).
        """
        if df_vix_5m is None or len(df_vix_5m) < 4:
            self.vix_direction = "NEUTRAL"
            return
        
        # Use last CLOSED candle
        last_closed = df_vix_5m.iloc[-1]
        prev_closed = df_vix_5m.iloc[-2]
        three_bar_prev = df_vix_5m.iloc[-4] if len(df_vix_5m) >= 4 else df_vix_5m.iloc[0]
        
        # Calculate VIX change
        vix_change_pct = ((last_closed['close'] - prev_closed['close']) / prev_closed['close']) * 100
        vix_3bar_change = ((last_closed['close'] - three_bar_prev['close']) / three_bar_prev['close']) * 100
        
        # Classify VIX state based on config thresholds
        spike_thresh = self.config.get('spike_threshold_pct', 3.0)
        spike_3bar_thresh = self.config.get('spike_3bar_threshold_pct', 5.0)
        rising_thresh = self.config.get('rising_threshold_pct', 0.5)
        rising_3bar_thresh = self.config.get('rising_3bar_threshold_pct', 1.5)
        falling_thresh = self.config.get('falling_threshold_pct', -0.5)
        falling_3bar_thresh = self.config.get('falling_3bar_threshold_pct', -1.5)

        if vix_change_pct > spike_thresh or vix_3bar_change > spike_3bar_thresh:
            self.vix_direction = "SPIKE"
        elif vix_change_pct > rising_thresh or vix_3bar_change > rising_3bar_thresh:
            self.vix_direction = "RISING"
        elif vix_change_pct < falling_thresh or vix_3bar_change < falling_3bar_thresh:
            self.vix_direction = "FALLING"
        else:
            self.vix_direction = "NEUTRAL"
        
        self.last_vix_close = last_closed['close']
        self.vix_change_pct = vix_change_pct
        self.vix_3bar_change = vix_3bar_change

    def filter_signal(self, direction: str, confidence: int) -> tuple:
        """
        Apply VIX bias to a trade signal.
        Returns: (adjusted_confidence: int, allowed: bool, reason: str)
        """
        if not self.enabled:
            return (confidence, True, "VIX_DISABLED")
        
        if self.vix_direction == "SPIKE":
            if direction == "CE":
                if self.config.get('spike_long_block', True):
                    return (confidence, False, "VIX_SPIKE_BLOCKS_LONGS")
                else:
                    return (confidence - 20, True, "VIX_SPIKE_PENALIZES_LONGS")
            else:
                boost = self.config.get('spike_short_boost', 15)
                return (confidence + boost, True, "VIX_SPIKE_FAVORS_SHORTS")
        
        elif self.vix_direction == "RISING":
            if direction == "CE":
                penalty = self.config.get('rising_long_penalty', 15)
                return (confidence - penalty, True, "VIX_RISING_PENALIZES_LONGS")
            else:
                boost = self.config.get('rising_short_boost', 10)
                return (confidence + boost, True, "VIX_RISING_FAVORS_SHORTS")
        
        elif self.vix_direction == "FALLING":
            if direction == "CE":
                boost = self.config.get('falling_long_boost', 10)
                return (confidence + boost, True, "VIX_FALLING_FAVORS_LONGS")
            else:
                penalty = self.config.get('falling_short_penalty', 15)
                return (confidence - penalty, True, "VIX_FALLING_PENALIZES_SHORTS")
        
        else:  # NEUTRAL
            return (confidence, True, "VIX_NEUTRAL")
    
    def get_status(self) -> dict:
        return {
            'direction': self.vix_direction,
            'last_close': self.last_vix_close,
            'enabled': self.enabled,
            'change_pct': getattr(self, 'vix_change_pct', 0),
            '3bar_change': getattr(self, 'vix_3bar_change', 0)
        }
