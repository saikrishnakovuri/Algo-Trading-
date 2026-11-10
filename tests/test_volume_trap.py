import pytest
import pandas as pd
import numpy as np
from modules.price_action_engine import PriceActionEngine

def make_df(volumes, opens=None, highs=None, lows=None, closes=None):
    if opens is None: opens = [100] * len(volumes)
    if highs is None: highs = [105] * len(volumes)
    if lows is None: lows = [95] * len(volumes)
    if closes is None: closes = [102] * len(volumes)
    
    return pd.DataFrame({
        'Open': opens, 'High': highs, 'Low': lows, 'Close': closes, 'Volume': volumes
    })

def test_detect_volume_spike_true():
    # 20 bars of low volume (100), 21st bar is high volume (200)
    # Mean of 20 = 100. 200 > 100 * 1.5.
    volumes = [100] * 20 + [200]
    df = make_df(volumes)
    assert PriceActionEngine.detect_volume_spike(df, period=20, multiplier=1.5) is True

def test_detect_volume_spike_false():
    volumes = [100] * 21
    df = make_df(volumes)
    assert PriceActionEngine.detect_volume_spike(df, period=20, multiplier=1.5) is False

def test_volume_confirmation_strong_bullish():
    # Spike + Close > Open
    volumes = [100] * 20 + [200]
    opens = [100] * 21
    closes = [100] * 20 + [110]
    df = make_df(volumes, opens=opens, closes=closes)
    assert PriceActionEngine.volume_confirmation(df) == 'STRONG_BULLISH'

def test_volume_confirmation_strong_bearish():
    # Spike + Close < Open
    volumes = [100] * 20 + [200]
    opens = [100] * 21
    closes = [100] * 20 + [90]
    df = make_df(volumes, opens=opens, closes=closes)
    assert PriceActionEngine.volume_confirmation(df) == 'STRONG_BEARISH'

def test_volume_confirmation_weak_move():
    # No Spike
    volumes = [100] * 21
    df = make_df(volumes)
    assert PriceActionEngine.volume_confirmation(df) == 'WEAK_MOVE'
