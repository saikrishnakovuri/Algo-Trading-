import os
import pandas as pd
import logging
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
from modules.strategy_selector import MasterStrategySelector
from modules.v3_utils import load_yaml
from pymongo import MongoClient
from datetime import datetime

logger = logging.getLogger("ScannerEngine")

def analyze_single_stock(symbol: str, df: pd.DataFrame, vix: float) -> Dict[str, Any]:
    """Worker function for parallel processing."""
    try:
        selector = MasterStrategySelector()
        signal = selector.select_best_signal(df, symbol, vix)
        if signal:
            return {
                "symbol": symbol,
                "status": "SIGNAL",
                "strategy": signal['strategy'],
                "direction": signal['direction'],
                "confidence": signal['confidence'],
                "entry": signal['entry_price'],
                "sl": signal['sl'],
                "tp": signal['tp'],
                "tags": signal['context_tags']
            }
        return {"symbol": symbol, "status": "NO_SIGNAL"}
    except Exception as e:
        return {"symbol": symbol, "status": "ERROR", "error": str(e)}

class ScannerEngine:
    """
    Phase 28: Parallel scanner for 1000+ stocks.
    """
    def __init__(self, max_workers: int = 4, db_url: str = None):
        self.max_workers = max_workers
        self.results = []
        if db_url:
            self.client = MongoClient(db_url)
            self.db = self.client["tradealert_db"]
        else:
            self.db = None

    def scan_universe(self, universe_data: Dict[str, pd.DataFrame], vix: float) -> List[Dict[str, Any]]:
        """
        Runs parallel scan across provided universe.
        """
        signals = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {
                executor.submit(analyze_single_stock, sym, df, vix): sym 
                for sym, df in universe_data.items() if df is not None and not df.empty
            }
            
            for future in as_completed(future_to_symbol):
                res = future.result()
                if res['status'] == "SIGNAL":
                    signals.append(res)
                elif res['status'] == "ERROR":
                    logger.warning(f"Scanner error for {res['symbol']}: {res['error']}")
                    
        self.results = sorted(signals, key=lambda x: x['confidence'], reverse=True)
        return self.results

    def save_results(self, signals: List[Dict], rs_rankings: List[Dict]):
        """REQ 28-3: Save scanner snapshot to MongoDB."""
        if not self.db: return
        
        snapshot = {
            "timestamp": datetime.now(),
            "signals": signals,
            "rankings": rs_rankings[:100] # Top 100 leaders
        }
        self.db.scanner_snapshots.insert_one(snapshot)
        logger.info(f"Scanner snapshot saved. {len(signals)} signals found.")
