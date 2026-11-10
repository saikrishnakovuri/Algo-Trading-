import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta

# Import modules from the project
from modules.broker_layer import AngelOneBroker
from modules.strategy_selector import MasterStrategySelector
from modules.context_detector import MarketContext

def run_backtest():
    print("Initializing Broker...")
    broker = AngelOneBroker()
    if not broker.login():
        print("Login failed.")
        return

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)
    
    # NIFTY Index is explicitly token 99926000 on NSE
    token_map["NIFTY"] = "99926000"

    symbols = [
        "NIFTY"
    ]

    print("Fetching today's 1m data...")
    all_1m_data = {}
    
    for sym in symbols:
        # NIFTY is an index, the others are equities (-EQ suffix in the mapping usually)
        token_key = f"{sym}-EQ" if sym != "NIFTY" else "NIFTY"
        token = token_map.get(token_key)
        
        if not token:
            print(f"Skipping {sym}, token not found.")
            continue
        
        if sym == "NIFTY":
            try:
                raw = broker.smart_api.getCandleData({
                    'exchange': 'NSE',
                    'symboltoken': token,
                    'interval': 'ONE_MINUTE',
                    'fromdate': '2026-05-20 09:15',
                    'todate': '2026-05-23 15:30'
                })
                if raw['status'] and raw['data']:
                    df = pd.DataFrame(raw['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    df.set_index('Timestamp', inplace=True)
                    df.columns = [c.lower() for c in df.columns]
                    all_1m_data[sym] = df
                    print(f"Loaded {len(df)} 1m bars for {sym}")
                else:
                    print(f"Failed to fetch data for {sym}")
            except Exception as e:
                print(f"Exception fetching {sym}: {e}")
        else:
            # Use broker.get_historical_data (which uses SmartAPI)
            # Fetching 2 days to ensure we have enough data for EMAs/indicators (50+ bars)
            df = broker.get_historical_data(token_key, token, interval="ONE_MINUTE", days=4)
            if df is not None and not df.empty:
                df.columns = [c.lower() for c in df.columns]
                all_1m_data[sym] = df
                print(f"Loaded {len(df)} 1m bars for {sym}")
            else:
                print(f"Failed to fetch data for {sym}")
        time.sleep(0.5)

    print("\nStarting Backtest Simulation with Forced Regime (TRENDING_DOWN)...")
    
    # Force the strategy selector's context detector to always return TRENDING_DOWN
    selector = MasterStrategySelector()
    
    # Monkey-patch context detector
    original_detect = selector.context_detector.detect
    def forced_detect(df, vix, current_time=None):
        ctx = original_detect(df, vix, current_time)
        # ctx.regime = "TRENDING_DOWN" # Let it detect the actual regime instead of forcing it
        return ctx
    selector.context_detector.detect = forced_detect

    # To mimic live trades, we need to:
    # 1. Iterate through time
    # 2. At each 5m boundary, run the selector
    # 3. If trade triggers, monitor 1m bars for SL/TP hits.
    
    # Get all unique 1m timestamps for today
    today_str = "2026-05-22"
    all_timestamps = set()
    for df in all_1m_data.values():
        today_data = df[df.index.astype(str).str.startswith(today_str)]
        all_timestamps.update(today_data.index)
    
    sorted_timestamps = sorted(list(all_timestamps))
    
    open_trades = []
    closed_trades = []
    
    for ts in sorted_timestamps:
        is_5m_boundary = ts.minute % 5 == 0
        
        # 1. Check open trades for SL/TP exits
        for trade in list(open_trades):
            sym = trade['symbol']
            if sym not in all_1m_data: continue
            
            df = all_1m_data[sym]
            if ts not in df.index: continue
            
            bar = df.loc[ts]
            high, low = bar['high'], bar['low']
            
            # Simple TP/SL logic mimicking the live engine
            exit_price = None
            exit_reason = None
            
            if trade['direction'] in ["CE", "BUY", "LONG"]:
                if trade.get('sl') is not None and low <= trade['sl']:
                    exit_price = trade['sl']
                    exit_reason = "STOP_LOSS"
                elif trade.get('tp') is not None and high >= trade['tp']:
                    exit_price = trade['tp']
                    exit_reason = "TARGET"
            else: # PE / SHORT
                if trade.get('sl') is not None and high >= trade['sl']:
                    exit_price = trade['sl']
                    exit_reason = "STOP_LOSS"
                elif trade.get('tp') is not None and low <= trade['tp']:
                    exit_price = trade['tp']
                    exit_reason = "TARGET"
                    
            if exit_price:
                # EOD Auto Square-off at 15:25
                if ts.hour == 15 and ts.minute >= 25:
                    exit_price = bar['close']
                    exit_reason = "EOD_CLOSE"
                    
                trade['exit_time'] = ts
                trade['exit_price'] = exit_price
                trade['exit_reason'] = exit_reason
                
                direction_mult = 1 if trade['direction'] in ["CE", "BUY", "LONG"] else -1
                trade['pnl'] = (exit_price - trade['entry_price']) * 75 * direction_mult # 75 qty like live
                
                closed_trades.append(trade)
                open_trades.remove(trade)
                
        # 2. At 5m boundaries, look for new trades
        if is_5m_boundary:
            # EOD check - don't enter new trades after 15:15
            if ts.hour == 15 and ts.minute >= 15: continue
            
            for sym, df_1m in all_1m_data.items():
                # Get historical data up to this timestamp
                df_up_to_now = df_1m.loc[:ts]
                
                # We need enough data for indicators (e.g. 50 bars on 5m = 250 mins)
                if len(df_up_to_now) < 100: continue
                
                # We only allow one open trade per symbol
                if any(t['symbol'] == sym for t in open_trades): continue
                
                # Resample to 5m
                # Ensure we don't include future data
                df_5m = df_up_to_now.resample('5min').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                
                if len(df_5m) < 50: continue
                
                # Select best signal
                try:
                    signal = selector.select_best_signal(df_5m, sym, vix=15.0, current_time=ts, mode="NORMAL")
                    if signal and signal['confidence'] >= 50:
                        open_trades.append({
                            'symbol': sym,
                            'strategy': signal['strategy'],
                            'direction': signal['direction'],
                            'entry_price': signal['entry_price'],
                            'sl': signal['sl'],
                            'tp': signal['tp'],
                            'entry_time': ts,
                            'confidence': signal['confidence']
                        })
                except Exception as e:
                    pass

    # EOD Auto square off any remaining open trades
    for trade in open_trades:
        sym = trade['symbol']
        df = all_1m_data[sym]
        last_bar = df.iloc[-1]
        trade['exit_time'] = last_bar.name
        trade['exit_price'] = last_bar['close']
        trade['exit_reason'] = "EOD_CLOSE"
        direction_mult = 1 if trade['direction'] in ["CE", "BUY", "LONG"] else -1
        trade['pnl'] = (trade['exit_price'] - trade['entry_price']) * 75 * direction_mult
        closed_trades.append(trade)

    print("\n" + "="*125)
    print(f"{'Symbol':<10} | {'Strategy':<20} | {'Side':<4} | {'Conf':<4} | {'Entry Time':<16} | {'Exit Time':<16} | {'Entry':<8} | {'Exit':<8} | {'PnL':<8} | {'Reason'}")
    print("-" * 125)
    
    total_pnl = 0
    for t in sorted(closed_trades, key=lambda x: x['entry_time']):
        total_pnl += t['pnl']
        et = t['entry_time'].strftime("%H:%M:%S")
        xt = t['exit_time'].strftime("%H:%M:%S")
        conf = int(t.get('confidence', 0))
        print(f"{t['symbol']:<10} | {t['strategy']:<20} | {t['side'] if 'side' in t else t['direction']:<4} | {conf:<4} | {et:<16} | {xt:<16} | {t['entry_price']:<8.2f} | {t['exit_price']:<8.2f} | {t['pnl']:<8.2f} | {t['exit_reason']}")
        
    print("-" * 125)
    print(f"Total Gross PnL: {total_pnl:.2f}")
    print("="*125)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    run_backtest()
