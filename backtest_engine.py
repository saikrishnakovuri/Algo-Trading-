import os
import csv
import pandas as pd
import numpy as np
from datetime import datetime, time as dtime
from modules.price_action_engine import PriceActionEngine
from modules.option_chain import fetch_option_chain

class BacktestEngine:
    """
    Simulates trades, logs them to a journal, and calculates performance metrics.
    """

    def __init__(self, initial_capital=100000.0):
        self.initial_capital = initial_capital
        self.journal_file = "trade_journal.csv"

    def log_trade(self, trade, filename=None):
        if filename is None: filename = self.journal_file
        file_exists = os.path.isfile(filename)
        with open(filename, "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=trade.keys())
            if not file_exists: writer.writeheader()
            writer.writerow(trade)

    def calculate_performance(self, trades):
        if not trades:
            return {"Total Trades": 0, "Wins": 0, "Losses": 0, "Win Rate %": 0, "Total Profit": 0, "Max Drawdown": 0, "RR Ratio": 0}
        wins, losses, total_profit = 0, 0, 0
        equity, peak, drawdown = self.initial_capital, self.initial_capital, 0
        win_pnls, loss_pnls = [], []
        for t in trades:
            pnl = float(t.get("pnl") or 0)
            if pnl > 0: wins += 1; win_pnls.append(pnl)
            elif pnl < 0: losses += 1; loss_pnls.append(abs(pnl))
            total_profit += pnl; equity += pnl
            peak = max(peak, equity); drawdown = max(drawdown, peak - equity)
        total_trades = len(trades)
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
        avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 1
        return {"Total Trades": total_trades, "Wins": wins, "Losses": losses, "Win Rate %": round(win_rate, 2), "Total Profit": round(total_profit, 2), "Max Drawdown": round(drawdown, 2), "RR Ratio": round(avg_win / avg_loss, 2)}

    def run_massive_backtest_v2(self, files: list, strategy_isolation_filter: str = None, start_date: str = None, end_date: str = None, data_interval_minutes: int = 1, step_size: int = 5, target_r_multiple: float = None):
        from modules.intermarket.feeds.manager import IntermarketFeedManager
        from modules.regime.integration import MarketRegimeAdapter
        from modules.vp_avwap.integration import VolumeProfileAdapter
        from modules.smc.integration import SMCAdapter
        from modules.intermarket.integration import IntermarketAdapter
        from modules.context_filters.integration import ContextFilterAdapter
        from modules.risk_exec.integration import RiskExecAdapter
        from modules.learning import LearningSystem

        all_trades, active_trades_per_stock = [], {}
        current_equity = self.initial_capital
        inter_manager = IntermarketFeedManager()
        
        # Adapters
        regime_adapter = MarketRegimeAdapter()
        vp_adapter = VolumeProfileAdapter()
        smc_adapter = SMCAdapter()
        intermarket_adapter = IntermarketAdapter()
        context_adapter = ContextFilterAdapter()
        risk_adapter = RiskExecAdapter()
        learning_system = LearningSystem()

        for file in files:
            symbol = os.path.basename(file).replace("_1m.csv", "")
            print(f"Analyzing {symbol}...")
            active_trades_per_stock[symbol] = set()
            smc_adapter.engine.ob_5m.reset(); smc_adapter.engine.ob_1m.reset()
            smc_adapter.engine.fvg_5m.reset(); smc_adapter.engine.fvg_1m.reset()

            try:
                df1 = pd.read_csv(file, index_col=0, parse_dates=True)
                df1.rename(columns={c: c.lower() for c in df1.columns}, inplace=True)
                for col in ['open', 'high', 'low', 'close', 'volume']: df1[col.capitalize()] = df1[col]
                if df1.index.tz is not None: df1.index = df1.index.tz_localize(None)
                if start_date: df1 = df1[df1.index >= start_date]
                if end_date: df1 = df1[df1.index <= end_date]
                if df1.empty: continue

                df5 = PriceActionEngine.resample_data(df1, '5min')
                df15 = PriceActionEngine.resample_data(df1, '15min')
                if len(df5) < 20 or len(df15) < 10: continue

                lookback, prior_session_close, last_day, cached_intermarket_ctx = 50, df1['close'].iloc[0], None, None

                for i in range(lookback, len(df1), step_size):
                    current_time = df1.index[i]
                    current_day = current_time.strftime("%Y-%m-%d")
                    
                    if last_day and current_day != last_day:
                        prev_day_data = df1[df1.index.strftime("%Y-%m-%d") == last_day]
                        if not prev_day_data.empty: prior_session_close = prev_day_data['close'].iloc[-1]
                        inter_manager.refresh_all(files, backtest_mode=True, current_date=current_time)
                        cached_intermarket_ctx = inter_manager.get_latest_contexts()

                    if cached_intermarket_ctx is None:
                        inter_manager.refresh_all(files, backtest_mode=True, current_date=current_time)
                        cached_intermarket_ctx = inter_manager.get_latest_contexts()

                    last_day = current_day
                    s1, s5, s15 = df1.iloc[:i+1], df5[df5.index <= current_time], df15[df15.index <= current_time]
                    if len(s5) < 20 or len(s15) < 10: continue

                    decision = PriceActionEngine.final_trading_decision(
                        {'15m': s15, '5m': s5, '1m': s1}, None, s5, symbol=symbol, 
                        prior_ohlc={'close': prior_session_close}, intermarket_context=cached_intermarket_ctx, 
                        backtest_mode=True, strategy_isolation_filter=strategy_isolation_filter,
                        regime_adapter=regime_adapter, vp_adapter=vp_adapter, smc_adapter=smc_adapter,
                        intermarket_adapter=intermarket_adapter, context_adapter=context_adapter,
                        risk_adapter=risk_adapter, learning_system=learning_system
                    )

                    if decision.get('trade') != 'NO TRADE':
                        trade_type = decision['trade']
                        trigger_price = decision.get('trigger_price', s1['close'].iloc[-1])
                        sl, target = decision.get('sl'), decision.get('target1')
                        
                        if sl is None or target is None:
                            continue

                        future = df1.iloc[i+1 : i+241]
                        triggered, trigger_index = False, -1
                        for idx, (_, row) in enumerate(future.iterrows()):
                            if (trade_type == 'CE' and row['high'] >= trigger_price) or (trade_type == 'PE' and row['low'] <= trigger_price):
                                triggered, trigger_index = True, idx; break
                        
                        if triggered:
                            entry = trigger_price
                            qty = int((current_equity * 0.01) / abs(entry - sl)) if abs(entry - sl) > 0 else 0
                            if qty == 0: continue
                            
                            trade_future = future.iloc[trigger_index + 1:]
                            exit_price, outcome = None, "OPEN"
                            for _, row in trade_future.iterrows():
                                if (trade_type == 'CE' and row['low'] <= sl) or (trade_type == 'PE' and row['high'] >= sl):
                                    exit_price, outcome = sl, "SL HIT"; break
                                if (trade_type == 'CE' and row['high'] >= target) or (trade_type == 'PE' and row['low'] <= target):
                                    exit_price, outcome = target, "TARGET HIT"; break
                            
                            if exit_price is None and not trade_future.empty: exit_price = trade_future['close'].iloc[-1]
                            elif exit_price is None: exit_price = entry

                            pnl = (exit_price - entry) * qty if trade_type == 'CE' else (entry - exit_price) * qty
                            current_equity += pnl
                            all_trades.append({"symbol": symbol, "date": current_time.strftime("%Y-%m-%d %H:%M"), "type": trade_type, "pnl": round(pnl, 2), "outcome": outcome})

            except Exception as e: print(f"Error processing {symbol}: {e}")

        if all_trades:
            report_name = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            pd.DataFrame(all_trades).to_excel(report_name, index=False)
            print(f"Report generated: {report_name}")
        return all_trades
