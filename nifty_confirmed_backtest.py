import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta

from modules.broker_layer import AngelOneBroker
from modules.strategy_selector import MasterStrategySelector

def run_nifty_confirmed_backtest():
    broker = AngelOneBroker()
    if not broker.login(): return

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)
    
    nifty_token = "99926000"

    raw = broker.smart_api.getCandleData({
        'exchange': 'NSE',
        'symboltoken': nifty_token,
        'interval': 'ONE_MINUTE',
        'fromdate': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
        'todate': datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    
    df_1m = pd.DataFrame(raw['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df_1m['Timestamp'] = pd.to_datetime(df_1m['Timestamp'])
    df_1m.set_index('Timestamp', inplace=True)
    df_1m.columns = [c.lower() for c in df_1m.columns]

    selector = MasterStrategySelector()
    original_detect = selector.context_detector.detect
    def forced_detect(df, vix, current_time=None):
        ctx = original_detect(df, vix, current_time)
        ctx.regime = "TRENDING_DOWN"
        return ctx
    selector.context_detector.detect = forced_detect

    today_str = "2026-05-21"
    today_data = df_1m[df_1m.index.astype(str).str.startswith(today_str)]
    sorted_timestamps = sorted(list(today_data.index))
    
    open_trades = []
    closed_trades = []
    pending_trade = None
    
    for ts in sorted_timestamps:
        is_5m_boundary = ts.minute % 5 == 0
        if ts not in df_1m.index: continue
        bar = df_1m.loc[ts]
        high, low = bar['high'], bar['low']
        
        # 1. Manage pending trade (Entry Confirmation)
        if pending_trade:
            triggered = False
            entry_price = 0
            if pending_trade['direction'] in ["CE", "BUY", "LONG"]:
                if high > pending_trade['trigger_price']:
                    triggered = True
                    entry_price = max(bar['open'], pending_trade['trigger_price'])
            else: # PE
                if low < pending_trade['trigger_price']:
                    triggered = True
                    entry_price = min(bar['open'], pending_trade['trigger_price'])
                    
            if triggered:
                open_trades.append({
                    'symbol': "NIFTY",
                    'strategy': pending_trade['strategy'],
                    'direction': pending_trade['direction'],
                    'entry_price': entry_price,
                    'sl': pending_trade['sl'],
                    'tp': pending_trade['tp'],
                    'signal_time': pending_trade['signal_time'],
                    'entry_time': ts, # Confirmed entry time
                    'confidence': pending_trade['confidence']
                })
                pending_trade = None

        # 2. Check open trades for SL/TP exits
        for trade in list(open_trades):
            exit_price = None
            if trade['direction'] in ["CE", "BUY", "LONG"]:
                if trade.get('sl') is not None and low <= trade['sl']:
                    exit_price = trade['sl']
                elif trade.get('tp') is not None and high >= trade['tp']:
                    exit_price = trade['tp']
            else:
                if trade.get('sl') is not None and high >= trade['sl']:
                    exit_price = trade['sl']
                elif trade.get('tp') is not None and low <= trade['tp']:
                    exit_price = trade['tp']
                    
            if exit_price:
                trade['exit_time'] = ts
                trade['exit_price'] = exit_price
                direction_mult = 1 if trade['direction'] in ["CE", "BUY", "LONG"] else -1
                trade['pnl'] = (exit_price - trade['entry_price']) * 75 * direction_mult
                closed_trades.append(trade)
                open_trades.remove(trade)
                
        # EOD Auto Square-off at 15:25
        if ts.hour == 15 and ts.minute >= 25:
             for trade in list(open_trades):
                trade['exit_time'] = ts
                trade['exit_price'] = bar['close']
                direction_mult = 1 if trade['direction'] in ["CE", "BUY", "LONG"] else -1
                trade['pnl'] = (trade['exit_price'] - trade['entry_price']) * 75 * direction_mult
                closed_trades.append(trade)
                open_trades.remove(trade)

        # 3. Generate new signals at 5m boundaries
        if is_5m_boundary:
            # Discard any pending trade that wasn't triggered in the last 5 minutes
            pending_trade = None
            
            if ts.hour == 15 and ts.minute >= 15: continue
            
            df_up_to_now = df_1m.loc[:ts]
            if len(df_up_to_now) < 100: continue
            if any(t['symbol'] == "NIFTY" for t in open_trades): continue
            
            df_5m = df_up_to_now.resample('5min').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
            
            if len(df_5m) < 50: continue
            
            try:
                signal = selector.select_best_signal(df_5m, "NIFTY", vix=15.0, current_time=ts, mode="NORMAL")
                if signal and signal['confidence'] >= 50:
                    # Trigger price is the high/low of the signal candle (the last 1m candle of the 5m block)
                    last_1m_high = df_up_to_now.iloc[-1]['high']
                    last_1m_low = df_up_to_now.iloc[-1]['low']
                    
                    trigger_price = last_1m_high if signal['direction'] in ["CE", "BUY", "LONG"] else last_1m_low
                    
                    pending_trade = {
                        'strategy': signal['strategy'],
                        'direction': signal['direction'],
                        'sl': signal['sl'],
                        'tp': signal['tp'],
                        'confidence': signal['confidence'],
                        'trigger_price': trigger_price,
                        'signal_time': ts
                    }
            except Exception:
                pass

    print("=" * 135)
    print(f"{'Strategy':<20} | {'Side':<4} | {'Signal Time':<12} | {'Entry Time':<12} | {'Exit Time':<12} | {'Conf %':<6} | {'Entry':<8} | {'SL':<8} | {'PnL':<8}")
    print("-" * 135)
    total_pnl = 0
    for t in sorted(closed_trades, key=lambda x: x['entry_time']):
        total_pnl += t['pnl']
        st = t['signal_time'].strftime("%H:%M:%S")
        et = t['entry_time'].strftime("%H:%M:%S")
        xt = t['exit_time'].strftime("%H:%M:%S")
        print(f"{t['strategy']:<20} | {t['direction']:<4} | {st:<12} | {et:<12} | {xt:<12} | {t['confidence']:<6.1f} | {t['entry_price']:<8.2f} | {t['sl']:<8.2f} | {t['pnl']:<8.2f}")
    print("-" * 135)
    print(f"Total NIFTY PnL (With Entry Confirmation): {total_pnl:.2f}")
    print("=" * 115)

if __name__ == "__main__":
    run_nifty_confirmed_backtest()
