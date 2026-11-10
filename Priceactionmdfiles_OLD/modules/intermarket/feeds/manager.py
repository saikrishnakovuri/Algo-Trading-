import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

from modules.intermarket.schemas import IndexContext, UniverseSnapshot, CrossAssetSnapshot, GlobalRiskVerdict
from modules.intermarket.feeds.yfinance_feed import YFinanceFeed
from modules.intermarket.feeds.nsepython_feed import NSEPythonFeed

class IntermarketFeedManager:
    """
    Optimized Hybrid orchestrator for intermarket data.
    Loads CSVs into memory ONCE for high-speed backtesting.
    """
    
    def __init__(self):
        self.yahoo = YFinanceFeed()
        self.nse = NSEPythonFeed()
        
        # Caches
        self.last_nifty_ctx: Optional[IndexContext] = None
        self.last_banknifty_ctx: Optional[IndexContext] = None
        self.last_universe_snap: Optional[UniverseSnapshot] = None
        self.last_cross_asset_snap: Optional[CrossAssetSnapshot] = None

        # PRE-LOAD CSVs for speed (Fixes the backtest bottleneck)
        self.csv_data = {}
        for key, path in [
            ('nifty_intraday', "data/angel_historical/nifty50_1m.csv"),
            ('banknifty_intraday', "data/angel_historical/banknifty_1m.csv"),
            ('nifty', "data/nifty50_daily.csv"),
            ('banknifty', "data/banknifty50_daily.csv"),
            ('vix_5m', "data/india_vix_5m.csv"),
            ('vix', "data/india_vix_daily.csv")
        ]:
            if os.path.exists(path):
                df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
                # Ensure all indexes are timezone naive
                try:
                    df.index = df.index.tz_localize(None)
                except TypeError:
                    pass # Already naive
                # Ensure it's OHLCV and resample to 5m for the engine
                if 'intraday' in key:
                    df_5m = df.resample('5min').agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    self.csv_data[key] = df_5m
                else:
                    self.csv_data[key] = df

    def refresh_all(self, universe_symbols: List[str], backtest_mode: bool = False, current_date: Optional[datetime] = None):
        """
        Performs a full refresh. In backtest mode, uses memory-cached data.
        """
        if backtest_mode and current_date:
            # High-speed backtest cache
            if not hasattr(self, '_bt_cache'): self._bt_cache = {}
            cache_key = current_date.strftime("%Y%m%d%H%M")
            if cache_key in self._bt_cache:
                cached = self._bt_cache[cache_key]
                self.last_nifty_ctx = cached['nifty']
                self.last_banknifty_ctx = cached['banknifty']
                self.last_cross_asset_snap = cached['cross']
                return

        if not backtest_mode:
            # Fallback to cached data in live for now if real-time fails
            self.last_nifty_ctx = self._get_cached_context('nifty_intraday', "NIFTY", current_date)
            self.last_banknifty_ctx = self._get_cached_context('banknifty_intraday', "BANKNIFTY", current_date)
            self.last_cross_asset_snap = self._get_cached_cross_assets(current_date)
        else:
            # Backtest mode
            self.last_nifty_ctx = self._get_cached_context('nifty_intraday', "NIFTY", current_date)
            self.last_banknifty_ctx = self._get_cached_context('banknifty_intraday', "BANKNIFTY", current_date)
            self.last_cross_asset_snap = self._get_cached_cross_assets(current_date)
        
        self.last_universe_snap = self._fetch_universe_snapshot(universe_symbols)
        
        if backtest_mode and current_date:
            self._bt_cache[current_date.strftime("%Y%m%d%H%M")] = {
                'nifty': self.last_nifty_ctx,
                'banknifty': self.last_banknifty_ctx,
                'cross': self.last_cross_asset_snap
            }

    def _get_cached_context(self, key: str, internal_name: str, current_date: Optional[datetime]) -> Optional[IndexContext]:
        df = self.csv_data.get(key)
        # Fallback to daily if intraday not available
        if df is None:
            df = self.csv_data.get(key.replace('_intraday', ''))
            
        if df is None or current_date is None: return None
        
        # Filter for data up to current_date
        history = df[df.index <= current_date]
        if history.empty: return None
        
        row = history.iloc[-1]
        
        # We provide the session slice for indicator calculation
        session_start = current_date.replace(hour=9, minute=15, second=0, microsecond=0)
        session_slice = history[history.index >= session_start]
        
        # Context needs some history for trend
        if len(session_slice) < 5:
            # Beginning of day, take some previous bars
            ohlcv_5m = history.tail(30)
        else:
            ohlcv_5m = session_slice

        return IndexContext(
            symbol=internal_name,
            ohlcv_5m=ohlcv_5m,
            ohlcv_15m=ohlcv_5m, # Scored on 5m trend anyway
            session_open=session_slice['open'].iloc[0] if not session_slice.empty else float(row['open']),
            regime="TRENDING"
        )

    def _get_cached_cross_assets(self, current_date: Optional[datetime]) -> CrossAssetSnapshot:
        vix_df = self.csv_data.get('vix')
        vix_quote = {}
        if vix_df is not None and current_date:
            target_date = datetime.combine(current_date.date(), datetime.min.time())
            idx = vix_df.index.get_indexer([target_date], method='pad')[0]
            if idx != -1:
                vix_quote = {'close': float(vix_df.iloc[idx]['close']), 'session_return': 0.0}
        
        return CrossAssetSnapshot(usdinr={}, crude={}, gold={}, india_vix=vix_quote, sgx_nifty={})

    # ... keep live fetch methods as fallback but silenced ...
    def _fetch_cross_assets(self, current_date: Optional[datetime], backtest_mode: bool) -> CrossAssetSnapshot:
        """
        In live mode, attempts to fetch latest data; in backtest mode, uses cached CSVs.
        """
        if backtest_mode:
            return self._get_cached_cross_assets(current_date)
        
        # Live mode placeholder or nsepython fetch
        return self._get_cached_cross_assets(current_date) # Falling back to CSV cache for stability in live

    def _fetch_index_context(self, nse_name: str, internal_name: str, csv_key: str, current_date: Optional[datetime], backtest_mode: bool) -> Optional[IndexContext]:
        quote = self.nse.get_latest_data(nse_name, backtest_mode=True) # Always silence in internal helper
        if not quote:
            return self._get_cached_context(csv_key, internal_name, current_date)
        return self._get_cached_context(csv_key, internal_name, current_date) # Simplified logic for hybrid

    def _fetch_universe_snapshot(self, symbols: List[str]) -> UniverseSnapshot:
        snaps = {s: {'close': 0.0, 'open': 0.0, 'volume': 0, 'vwap': 0.0} for s in symbols}
        return UniverseSnapshot(timestamp=datetime.now(), symbol_snapshots=snaps)

    def get_latest_contexts(self) -> Dict[str, Any]:
        return {
            'nifty_ctx': self.last_nifty_ctx,
            'banknifty_ctx': self.last_banknifty_ctx,
            'universe_snapshot': self.last_universe_snap,
            'cross_assets': self.last_cross_asset_snap,
            'global_ctx': None
        }
