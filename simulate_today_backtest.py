from modules.broker_layer import AngelOneBroker
import pandas as pd
from datetime import datetime, timedelta
from modules.strategy_selector import MasterStrategySelector
import logging

# Setup basic logging to see the "live" output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("BacktestSim")

def run_simulation():
    broker = AngelOneBroker()
    broker.login()
    
    today = "2026-05-25"
    logger.info(f"--- FETCHING DATA FOR {today} ---")
    
    # 1. Fetch 5m and 1m data
    # We fetch a bit of yesterday too to satisfy the 50-bar requirement
    from_date = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d 09:15")
    to_date = today + " 15:30"
    
    df_5m_full = broker.get_historical_data(symbol="NIFTY", token="99926000", interval="FIVE_MINUTE", from_date_str=from_date, to_date_str=to_date)
    df_1m_full = broker.get_historical_data(symbol="NIFTY", token="99926000", interval="ONE_MINUTE", from_date_str=from_date, to_date_str=to_date)
    
    if df_5m_full is None or df_1m_full is None:
        logger.error("Failed to fetch data")
        return

    # Normalize columns
    df_5m_full.columns = [c.lower() for c in df_5m_full.columns]
    df_1m_full.columns = [c.lower() for c in df_1m_full.columns]

    selector = MasterStrategySelector()
    
    # Find start index for today in 5m df
    today_dt = pd.to_datetime(today).date()
    today_indices = [i for i, ts in enumerate(df_5m_full.index) if ts.date() == today_dt]
    
    if not today_indices:
        logger.error("No data for today found in fetched dataframe")
        return
        
    start_idx = today_indices[0]
    
    logger.info(f"--- STARTING SIMULATION FROM {df_5m_full.index[start_idx]} ---")
    
    trades = []
    
    # Loop through each candle of today
    for i in range(start_idx, len(df_5m_full)):
        current_ts = df_5m_full.index[i]
        
        # Slice "current" data (all data up to this candle)
        df_5m_sim = df_5m_full.iloc[:i+1]
        df_1m_sim = df_1m_full[df_1m_full.index <= current_ts]
        
        # We need at least 50 bars for context detector
        if len(df_5m_sim) < 50:
            continue
            
        # Run Selector
        # Note: We use VIX=17.0 as a proxy for today
        res = selector.select_best_signal(
            df_5m = df_5m_sim,
            df_1m = df_1m_sim,
            symbol = "NIFTY",
            vix = 17.0,
            current_time = current_ts.to_pydatetime(),
            mode = "NORMAL"
        )
        
        if res:
            logger.info(f"🔥 SIGNAL TRIGGERED AT {current_ts}")
            logger.info(f"   Strategy: {res['strategy']} | Direction: {res['direction']} | Conf: {res['confidence']:.1f}%")
            logger.info(f"   Regime: {res['context'].regime} | Structure: {res['context'].structure}")
            trades.append(res)

    logger.info("--- SIMULATION COMPLETE ---")
    logger.info(f"Total Signals: {len(trades)}")
    
    # Print the Funnel Report to see rejections
    print(selector.funnel_report())

if __name__ == "__main__":
    run_simulation()
