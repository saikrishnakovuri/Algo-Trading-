import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime, timedelta

from modules.broker_layer import AngelOneBroker

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/backtest_cache")

def pull_historical_data(symbols: List[str], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, pd.DataFrame]:
    """
    Pulls 1-minute historical data from Angel One for the requested symbols.
    Handles date ranges. If none provided, fetches the last 2 days.
    Chunks requests if the range is greater than 25 days to respect API limits.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    broker = AngelOneBroker()
    if not broker.login():
        logger.error("Failed to login to Angel One for historical data.")
        return {}

    token_file = Path("broker_tokens.json")
    if not token_file.exists():
        logger.error("broker_tokens.json not found.")
        return {}
        
    with open(token_file, "r") as f:
        token_map = json.load(f)
        
    # Ensure NIFTY is correct
    token_map["NIFTY"] = "99926000"

    end_dt = end_date or datetime.now()
    start_dt = start_date or (end_dt - timedelta(days=2))
    
    date_suffix = f"{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}"
    
    all_data = {}
    
    logger.info("Fetching historical data from %s to %s", start_dt.strftime('%Y-%m-%d %H:%M'), end_dt.strftime('%Y-%m-%d %H:%M'))
    
    for sym in symbols:
        cache_file = CACHE_DIR / f"{sym}_{date_suffix}.csv"
        
        # Check cache first
        if cache_file.exists():
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            all_data[sym] = df
            logger.info("Loaded %s from cache (%d rows)", sym, len(df))
            continue
            
        token_key = f"{sym}-EQ" if sym != "NIFTY" else "NIFTY"
        token = token_map.get(token_key)
        
        if not token:
            logger.warning("Token not found for symbol: %s", sym)
            continue
            
        logger.info("Downloading data for %s...", sym)
        
        # Chunking logic (max 30 days per call, using 25 for safety)
        current_start = start_dt
        chunks = []
        
        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=25), end_dt)
            
            from_date_str = current_start.strftime('%Y-%m-%d %H:%M')
            to_date_str = current_end.strftime('%Y-%m-%d %H:%M')
            
            if sym == "NIFTY":
                try:
                    raw = broker.smart_api.getCandleData({
                        'exchange': 'NSE',
                        'symboltoken': token,
                        'interval': 'ONE_MINUTE',
                        'fromdate': from_date_str,
                        'todate': to_date_str
                    })
                    if raw and raw.get('status') and raw.get('data'):
                        chunk_df = pd.DataFrame(raw['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                        chunk_df['Timestamp'] = pd.to_datetime(chunk_df['Timestamp'])
                        chunk_df.set_index('Timestamp', inplace=True)
                        chunk_df.columns = [c.lower() for c in chunk_df.columns]
                        chunks.append(chunk_df)
                    else:
                        logger.warning("Failed to fetch NIFTY chunk %s to %s: %s", from_date_str, to_date_str, raw)
                except Exception as e:
                    logger.error("Exception fetching NIFTY chunk: %s", e)
            else:
                # Equity logic
                chunk_df = broker.get_historical_data(token_key, token, interval="ONE_MINUTE", 
                                                from_date_str=from_date_str, to_date_str=to_date_str)
                if chunk_df is not None and not chunk_df.empty:
                    chunk_df.columns = [c.lower() for c in chunk_df.columns]
                    chunks.append(chunk_df)
                else:
                    logger.warning("Failed to fetch data chunk for %s from %s to %s", sym, from_date_str, to_date_str)
            
            current_start = current_end + timedelta(minutes=1)
            time.sleep(0.5) # Respect rate limits
            
        if chunks:
            combined_df = pd.concat(chunks)
            # Drop any potential duplicates from overlapping chunks
            combined_df = combined_df[~combined_df.index.duplicated(keep='first')].sort_index()
            combined_df.to_csv(cache_file)
            all_data[sym] = combined_df
            logger.info("Successfully fetched %d rows for %s", len(combined_df), sym)
        else:
            logger.warning("No data retrieved for %s in this date range.", sym)
        
    return all_data

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_symbols = ["ADANIENT", "NIFTY"]
    pull_historical_data(test_symbols)
