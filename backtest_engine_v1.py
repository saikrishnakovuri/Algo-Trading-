import os
import csv
import pandas as pd
import numpy as np
from datetime import datetime
from modules.price_action_engine import PriceActionEngine
from modules.option_chain import fetch_option_chain

class BacktestEngine:
    """
    Simulates trades, logs them to a journal, and calculates performance metrics.
    """

    def __init__(self, initial_capital=100000.0):
        self.initial_capital = initial_capital
        self.journal_file = "trade_journal.csv"

    def backtest(self, df_15m, df_5m, df_1m, strategy_func):
        """
        Simulate trades over historical data.
        strategy_func: should be PriceActionEngine.final_trading_decision or similar
        """
        trades = []
        # We need alignment across timeframes. For simplicity in this engine, 
        # we iterate through the common timestamps of the smallest timeframe 
        # that have enough lookback in the larger ones.
        
        # In a real backtest, you'd align indices carefully. 
        # For this implementation, we'll follow the user's provided structure.
        
        # User logic for outcome simulation
        # Note: final_trading_decision expects (mtf_analyses, option_df, price_df)
        
        # We'll skip the loop implementation for now and focus on the core logic provided 
        # as the user wants to integrate their specific code snippets.
        pass

    def log_trade(self, trade, filename=None):
        if filename is None:
            filename = self.journal_file
        
        file_exists = os.path.isfile(filename)
        with open(filename, "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=trade.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(trade)

    def calculate_performance(self, trades):
        if not trades:
            return {
                "Total Trades": 0, "Wins": 0, "Losses": 0, "Win Rate %": 0,
                "Total Profit": 0, "Max Drawdown": 0, "RR Ratio": 0
            }

        wins = 0
        losses = 0
        total_profit = 0
        equity = self.initial_capital
        peak = self.initial_capital
        drawdown = 0
        win_pnls = []
        loss_pnls = []

        for t in trades:
            pnl = float(t.get("pnl") or 0)
            outcome = t.get("outcome")

            if pnl > 0:
                wins += 1
                win_pnls.append(pnl)
            elif pnl < 0:
                losses += 1
                loss_pnls.append(abs(pnl))
            
            total_profit += pnl
            equity += pnl

            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)

        total_trades = len(trades)
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        # Correct RR Formula: Avg Win / Avg Loss
        avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
        avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 1
        rr_ratio = round(avg_win / avg_loss, 2)

        return {
            "Total Trades": total_trades,
            "Wins": wins,
            "Losses": losses,
            "Win Rate %": round(win_rate, 2),
            "Total Profit": round(total_profit, 2),
            "Max Drawdown": round(drawdown, 2),
            "RR Ratio": rr_ratio
        }

    def run_massive_backtest_v2(self, files: list, target_date: str = None, strategy_isolation_filter: str = None):
        """
        Runs backtest with elite safety filters.
        target_date: Format "YYYY-MM-DD"
        """
        from modules.price_action_engine import PriceActionEngine
        from modules.intermarket.feeds.manager import IntermarketFeedManager
        
        all_trades = []
        active_trades_per_stock = {} 
        current_equity = self.initial_capital 
        
        inter_manager = IntermarketFeedManager()
        
        # P1.5: Risk Controls
        MAX_DAILY_LOSS_PCT = 0.02 # 2% Max Daily Loss
        MAX_CONCURRENT_POSITIONS = 3 # Max 3 active trades per stock in this simulation
        daily_pnls = {} # Track PnL per day
        open_positions = [] # Track currently open positions globally across all stocks
        
        for file in files:
            symbol = os.path.basename(file).replace("_1m.csv", "")
            print(f"Analyzing {symbol}...")
            active_trades_per_stock[symbol] = set()
            
            try:
                df1 = pd.read_csv(file, index_col=0, parse_dates=True)
                # Standardize TitleCase
                rename_map = {c.lower(): c.capitalize() for c in df1.columns}
                df1.rename(columns=rename_map, inplace=True)
                
                # Add lowercase duplicates for downstream modules
                df1['high'] = df1['High']
                df1['low'] = df1['Low']
                df1['close'] = df1['Close']
                df1['open'] = df1['Open']
                df1['volume'] = df1['Volume']
                
                # Fix: Convert to tz-naive for consistency
                if df1.index.tz is not None:
                    df1.index = df1.index.tz_localize(None)

                if df1.empty: continue
                
                # ... (resampling logic)
                df5 = PriceActionEngine.resample_data(df1, '5min')
                df15 = PriceActionEngine.resample_data(df1, '15min')
                
                if len(df5) < 20 or len(df15) < 10: continue
                
                lookback = 50
                prior_session_close = df1['Close'].iloc[0] # Fallback
                last_day = None
                cached_intermarket_ctx = None
                
                # Corrected loop to iterate from start of data (plus lookback) to end
                for i in range(lookback, len(df1), 5):
                    current_time = df1.index[i]
                    current_day = current_time.strftime("%Y-%m-%d")
                    
                    if last_day and current_day != last_day:
                        # New day detected!
                        prev_day_data = df1[df1.index.strftime("%Y-%m-%d") == last_day]
                        if not prev_day_data.empty:
                            prior_session_close = PriceActionEngine._safe_float(prev_day_data['Close'].iloc[-1])
                        
                        # FIX 1: Refresh Intermarket Context ONCE PER DAY
                        try:
                            inter_manager.refresh_all(files, backtest_mode=True, current_date=current_time)
                            cached_intermarket_ctx = inter_manager.get_latest_contexts()
                        except Exception as e_refresh:
                            print(f"Error refreshing daily feeds for {current_day}: {e_refresh}")
                    
                    if cached_intermarket_ctx is None:
                        # Initial refresh for first day
                        inter_manager.refresh_all(files, backtest_mode=True, current_date=current_time)
                        cached_intermarket_ctx = inter_manager.get_latest_contexts()

                    last_day = current_day
                    ce_count = sum(1 for p in open_positions if p['type'] == 'CE')
                    pe_count = sum(1 for p in open_positions if p['type'] == 'PE')
                    
                    # Max 2 concurrent positions in one direction globally
                    MAX_SIDE_POSITIONS = 2
                    
                    # Daily Loss Ceiling Check
                    day_pnl = daily_pnls.get(current_day, 0)
                    if day_pnl < -(current_equity * MAX_DAILY_LOSS_PCT):
                        continue

                    # Time Filter removed from here (it's already in final_trading_decision)
                    # This was redundant and blocking trades.

                    s1 = df1.iloc[:i+1]
                    s5 = df5[df5.index <= current_time]
                    s15 = df15[df15.index <= current_time]
                    
                    
                    if len(s5) < 20 or len(s15) < 10: continue 
                    
                    # Portfolio Heat Cap (Per symbol in this sequential loop)
                    if len(active_trades_per_stock[symbol]) >= MAX_CONCURRENT_POSITIONS:
                        continue

                    mtf_analyses = {'15m': s15, '5m': s5, '1m': s1}
                    if s15 is None or s5 is None or s1 is None:
                        continue
                        
                    current_price = PriceActionEngine._safe_float(s1['Close'].iloc[-1])
                    
                    option_df = pd.DataFrame({
                        'strike': [current_price], 'CE_OI': [1000], 'PE_OI': [1000],
                        'CE_change': [0], 'PE_change': [0]
                    })
                    
                    try:
                        prior_ohlc = {'close': prior_session_close} if prior_session_close else {}
                        
                        # FIX: Refresh Intermarket Context
                        inter_manager.refresh_all(files, backtest_mode=True, current_date=current_time)
                        intermarket_ctx = inter_manager.get_latest_contexts()
                        
                        # --- NEW PRECISION FILTERS ---
                        entry_time = current_time.time()
                        from datetime import time as dtime
                        
                        # FIX: Pass backtest_mode=True AND intermarket_context AND isolation_filter
                        decision = PriceActionEngine.final_trading_decision(mtf_analyses, option_df, s5, symbol=symbol, prior_ohlc=prior_ohlc, intermarket_context=intermarket_ctx, backtest_mode=True, strategy_isolation_filter=strategy_isolation_filter)
                        
                        if decision is not None and decision.get('trade') != 'NO TRADE':
                            trade_type = decision.get('trade')
                            score = decision.get('checklist_score', 0)
                            
                            # FILTER 1: AFTERNOON CE RESTRICTION
                            if trade_type == "CE" and entry_time >= dtime(11, 30):
                                if score < 7.0:
                                    print(f"VETO: AFTERNOON CE | {symbol} | Score: {score:.2f}")
                                    decision['trade'] = 'NO TRADE'
                                    decision['reasons'].append(f"Afternoon CE Veto (Score {score:.2f} < 7.0)")
                                    
                            # FILTER 2: ENTRY MOMENTUM CONFIRMATION
                            if decision['trade'] != 'NO TRADE':
                                last_3_closes = [
                                    PriceActionEngine._safe_float(s1.iloc[-3]['Close']),
                                    PriceActionEngine._safe_float(s1.iloc[-2]['Close']),
                                    PriceActionEngine._safe_float(s1.iloc[-1]['Close'])
                                ]
                                
                                if trade_type == "CE":
                                    momentum_ok = last_3_closes[-1] > last_3_closes[0]
                                else:
                                    momentum_ok = last_3_closes[-1] < last_3_closes[0]
                                    
                                if not momentum_ok:
                                    print(f"VETO: MOMENTUM | {symbol} | {trade_type} | Closes: {last_3_closes}")
                                    decision['trade'] = 'NO TRADE'
                                    decision['reasons'].append(f"Momentum Veto (Closes: {last_3_closes})")
                                
                    except Exception as e_dec:
                        print(f"Error in decision for {symbol}: {e_dec}")
                        continue
                    
                    if decision is not None and decision.get('trade') != 'NO TRADE' and decision.get('entry') is not None:
                        # W4: Directional Bias Check
                        trade_type = decision.get('trade')
                        if trade_type == 'CE' and ce_count >= MAX_SIDE_POSITIONS: continue
                        if trade_type == 'PE' and pe_count >= MAX_SIDE_POSITIONS: continue
                        
                        # 1. DUPLICATE TRADE PREVENTION
                        zone_id = "NoZone"
                        supports, resistances = PriceActionEngine.find_support_resistance(s5)
                        if trade_type == 'CE' and supports and len(supports) > 0:
                            zone_id = round(supports[0]['center'], 2)
                        elif trade_type == 'PE' and resistances and len(resistances) > 0:
                            zone_id = round(resistances[0]['center'], 2)
                        
                        trade_key = f"{trade_type}_{zone_id}"
                        if symbol in active_trades_per_stock and trade_key in active_trades_per_stock[symbol]:
                            continue
                        
                        future = df1.iloc[i+1 : i+241] 
                        trigger_price = decision.get('trigger_price')
                        trade_type = decision['trade']
                        
                        triggered = False
                        trigger_index = -1
                        for idx, (_, row) in enumerate(future.iterrows()):
                            curr_low = PriceActionEngine._safe_float(row["Low"])
                            curr_high = PriceActionEngine._safe_float(row["High"])
                            if trade_type == 'CE' and curr_high >= trigger_price:
                                triggered = True; trigger_index = idx; break
                            if trade_type == 'PE' and curr_low <= trigger_price:
                                triggered = True; trigger_index = idx; break
                        
                        if not triggered: continue
                        
                        active_trades_per_stock[symbol].add(trade_key)
                        trade_future = future.iloc[trigger_index + 1:]
                        if trade_future.empty: continue

                        outcome = "OPEN"
                        
                        # UPGRADE 6: Spread-Adjusted Slippage (Liquidity Tiers)
                        LIQUID_STOCKS = ['RELIANCE', 'HDFCBANK', 'TCS', 'INFY', 'ICICIBANK', 'SBIN', 'AXISBANK']
                        MID_CAP_STOCKS = ['TORNTPHARM', 'JINDALSTEL', 'PATANJALI', 'ABB', 'ADANIENT']
                        
                        if symbol in LIQUID_STOCKS:
                            slippage_factor = 0.0005 # 5 bps
                        elif symbol in MID_CAP_STOCKS:
                            slippage_factor = 0.0015 # 15 bps
                        else:
                            slippage_factor = 0.0025 # 25 bps (small caps)

                        # --- ENTRY LOGIC ---
                        # Trigger price is our Limit Price. 
                        # In backtest, we assume we get filled AT the trigger price if it's hit.
                        # We apply slippage ONLY to simulate market impact/execution lag.
                        entry = trigger_price + (trigger_price * slippage_factor) if trade_type == 'CE' else trigger_price - (trigger_price * slippage_factor)
                        
                        original_sl = decision['sl']
                        target = decision['target1']
                        if original_sl is None or target is None: continue

                        # SAFETY: Ensure target is actually in profitable direction
                        if trade_type == 'CE' and target <= entry:
                             target = entry + abs(entry - original_sl) * 2.5
                        elif trade_type == 'PE' and target >= entry:
                             target = entry - abs(entry - original_sl) * 2.5
                        
                        # UPGRADE 2: Two-Stage Stop Loss (Initial + Breakeven Trail)
                        # Phase 1: Wider initial SL (already calculated in PriceActionEngine)
                        dist_to_sl = abs(entry - original_sl)
                        # Trigger Breakeven once RR 1.0:1 is achieved
                        rr_trigger = entry + (dist_to_sl * 1.0) if trade_type == 'CE' else entry - (dist_to_sl * 1.0)
                        
                        sl = original_sl
                        hit_breakeven = False
                        exit_price = None

                        # W7: DYNAMIC POSITION SIZING (Using current_equity instead of fixed 100k)
                        score = decision.get('checklist_score', 0)
                        risk_pct = 0.01 if score >= 8.5 else 0.005
                            
                        risk_per_trade = current_equity * risk_pct
                        risk_per_share = abs(entry - original_sl)
                        qty = int(risk_per_trade / risk_per_share) if risk_per_share > 0 else 0
                        qty = min(qty, int(current_equity / entry)) if entry > 0 else 0
                        if qty == 0: continue
                        
                        for bars_passed, (_, row) in enumerate(trade_future.iterrows()):
                            curr_low = PriceActionEngine._safe_float(row["Low"])
                            curr_high = PriceActionEngine._safe_float(row["High"])
                            curr_close = PriceActionEngine._safe_float(row["Close"])

                            # TWO-STAGE MOMENTUM CHECK (Optimization)
                            dist = (curr_close - entry) if trade_type == 'CE' else (entry - curr_close)
                            current_r = dist / dist_to_sl if dist_to_sl > 0 else 0

                            # GRADUATED TIME MANAGEMENT
                            # 20 min: If losing, cut immediately
                            if bars_passed == 20 and current_r < 0:
                                outcome = "TIME_CUT_20M_LOSING"
                                exit_price = curr_close; break

                            # 45 min: If below 0.5R, move SL to entry (breakeven protection)
                            if bars_passed == 45 and not hit_breakeven:
                                if current_r > 0 and current_r < 0.5:
                                    sl = entry; hit_breakeven = True
                                elif current_r <= 0:
                                    outcome = "TIME_CUT_45M_STALLED"
                                    exit_price = curr_close; break

                            # 90 min: Hard close anything still open below 1.0R
                            if bars_passed == 90:
                                if current_r < 1.0:
                                    outcome = "TIME_CUT_90M_FINAL"
                                    exit_price = curr_close; break
                            
                            # 150 min (2.5 hours): Absolute hard close for day trades
                            if bars_passed == 150:
                                outcome = "TIME_CUT_EOD"
                                exit_price = curr_close; break
                            
                            # Move to Breakeven after 1.0R (already achieved if rr_trigger hit)
                            if not hit_breakeven:
                                if trade_type == "CE" and curr_high >= rr_trigger:
                                    sl = entry; hit_breakeven = True
                                elif trade_type == "PE" and curr_low <= rr_trigger:
                                    sl = entry; hit_breakeven = True

                            if trade_type == "CE":
                                if curr_low <= sl: 
                                    outcome = "BREAKEVEN" if hit_breakeven else "SL HIT"
                                    exit_price = sl; break
                                if curr_high >= target: 
                                    outcome = "TARGET HIT"; exit_price = target; break
                            else:
                                if curr_high >= sl: 
                                    outcome = "BREAKEVEN" if hit_breakeven else "SL HIT"
                                    exit_price = sl; break
                                if curr_low <= target: 
                                    outcome = "TARGET HIT"; exit_price = target; break
                        
                        if exit_price is None:
                            if not trade_future.empty:
                                exit_price = PriceActionEngine._safe_float(trade_future.iloc[-1]['Close'])
                                outcome = "PARTIAL PROFIT (OPEN)" if hit_breakeven else "OPEN"
                            else:
                                exit_price = entry; outcome = "EXPIRED/NO DATA"
                        
                        # Apply slippage ONLY to Market/Force exits. 
                        # Target Hit and SL Hit are Limit/SL orders (already have buffer in live)
                        is_market_exit = outcome in ["FORCE_CLOSE_30M_STALLED", "BREAKEVEN", "TIME_STOP", "PARTIAL PROFIT (OPEN)", "OPEN"]
                        
                        if is_market_exit:
                            exit_price = exit_price - (exit_price * slippage_factor) if trade_type == 'CE' else exit_price + (exit_price * slippage_factor)
                        
                        # Corrected PnL directionality for CE and PE
                        if trade_type == 'CE':
                            pnl = (exit_price - entry) * qty
                        else:
                            pnl = (entry - exit_price) * qty

                        # Update Equity for Next Trade (Compounding)
                        current_equity += pnl

                        trade_record = {
                            "symbol": symbol, "date": current_time.strftime("%Y-%m-%d %H:%M"),
                            "time": current_time.strftime("%H:%M"), "type": trade_type,
                            "setup": decision.get('setup', 'ZONE_REJECTION'), "qty": qty,
                            "entry": entry, "sl": original_sl, "target": target,
                            "outcome": outcome, "score": decision.get('checklist_score', 0),
                            "pnl": round(pnl, 2)
                        }
                        all_trades.append(trade_record)
                        self.log_trade(trade_record)
                        from meta_learning.tracker import log_trade as meta_log
                        meta_log(trade_record)
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                
        if all_trades:
            df_report = pd.DataFrame(all_trades)
            df_report['PnL'] = df_report['pnl']
            report_name = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df_report.to_excel(report_name, index=False)
            print(f"Massive Backtest Report generated: {report_name}")
            
        return all_trades
