
import os

# Paths
root_engine = '../backtest_engine.py'
dashboard_page = '../AlgoTradingTelegramBotAndFrontend/frontend/src/pages/Dashboard.jsx'
backtesting_page = '../AlgoTradingTelegramBotAndFrontend/frontend/src/pages/Backtesting.jsx'

def fix_root_engine():
    if not os.path.exists(root_engine): return
    with open(root_engine, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ensure run function is correct
    if 'def run(config):' not in content:
        print("Run function not found in root engine. Adding it.")
        run_func = """
def run(config):
    \"\"\"Standalone entry point for backend server. Matches frontend expected schema.\"\"\"
    engine = BacktestEngine(initial_capital=float(config.get("capital", 1000000)))
    
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nifty200")
    files = []
    stocks = config.get("stocks", ["NIFTY"])
    
    mapping = {"NIFTY": "nifty50_1m.csv", "BANKNIFTY": "banknifty_1m.csv"}
    hist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "angel_historical")

    for s in stocks:
        mapped_name = mapping.get(s, f"{s}_1m.csv")
        fpath = os.path.join(hist_dir, mapped_name)
        if not os.path.exists(fpath):
            fpath = os.path.join(data_dir, f"{s}_1m.csv")
        if os.path.exists(fpath):
            files.append(fpath)

    raw_trades = engine.run_massive_backtest_v2(
        files=files,
        start_date=config.get("start_date"),
        end_date=config.get("end_date"),
        strategy_isolation_filter=config.get("entry_strategy")
    )

    formatted_trades = []
    for t in raw_trades:
        formatted_trades.append({
            **t,
            "net_pnl": t.get("pnl", 0),
            "entry_price": t.get("entry", 0),
            "exit_price": t.get("entry", 0) + (t.get("pnl", 0) / t.get("qty", 1)) if t.get("qty", 0) > 0 else t.get("entry", 0),
            "entry_time": t.get("date", ""),
        })

    stats = engine.calculate_performance(raw_trades)
    return {
        "metrics": {
            "total_trades": stats.get("Total Trades", 0),
            "win_rate": stats.get("Win Rate %", 0),
            "total_pnl": stats.get("Total Profit", 0),
            "profit_factor": stats.get("RR Ratio", 0),
        },
        "trades": formatted_trades
    }
"""
        content += run_func
    else:
        # Just fix the metrics mapping if already exists
        content = content.replace('stats.get("total_trades", 0)', 'stats.get("Total Trades", 0)')
        content = content.replace('stats.get("win_rate", 0)', 'stats.get("Win Rate %", 0)')
        content = content.replace('stats.get("total_pnl", 0)', 'stats.get("Total Profit", 0)')
        content = content.replace('stats.get("profit_factor", 0)', 'stats.get("RR Ratio", 0)')

    with open(root_engine, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_dashboard():
    if not os.path.exists(dashboard_page): return
    with open(dashboard_page, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add a "Quick Links" section to Dashboard
    if 'Quick Links' not in content:
        insertion_point = content.find('<div className="p-8 space-y-8">')
        if insertion_point != -1:
            insertion_point += len('<div className="p-8 space-y-8">')
            quick_links = """
      {/* Quick Links for Integration Visibility */}
      <div className="flex flex-wrap gap-4 mb-4">
        <a href="/control-center" className="px-4 py-2 bg-[#00bcd4]/10 border border-[#00bcd4]/30 rounded-lg text-[#00bcd4] text-xs font-bold hover:bg-[#00bcd4]/20 transition-all">âš™ï¸Ž CONTROL CENTER</a>
        <a href="/pa-engine" className="px-4 py-2 bg-purple-500/10 border border-purple-500/30 rounded-lg text-purple-400 text-xs font-bold hover:bg-purple-500/20 transition-all">âš’ï¸Ž PA ENGINE</a>
        <a href="/journal" className="px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-xs font-bold hover:bg-green-500/20 transition-all">ðŸ““ TRADE JOURNAL</a>
        <a href="/backtest" className="px-4 py-2 bg-orange-500/10 border border-orange-500/30 rounded-lg text-orange-400 text-xs font-bold hover:bg-orange-500/20 transition-all">â–¶ï¸Ž RUN BACKTEST</a>
        <a href="/config-explorer" className="px-4 py-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400 text-xs font-bold hover:bg-blue-500/20 transition-all">ðŸ“  CONFIG EXPLORER</a>
      </div>
"""
            content = content[:insertion_point] + quick_links + content[insertion_point:]
            
    with open(dashboard_page, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_backtesting():
    if not os.path.exists(backtesting_page): return
    with open(backtesting_page, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add optional chaining to metrics display to prevent crashes
    content = content.replace('{result.metrics.total_trades}', '{result?.metrics?.total_trades || 0}')
    content = content.replace('{result.metrics.win_rate}', '{result?.metrics?.win_rate || 0}')
    content = content.replace('{result.metrics.profit_factor}', '{result?.metrics?.profit_factor || 0}')
    
    with open(backtesting_page, 'w', encoding='utf-8') as f:
        f.write(content)

fix_root_engine()
fix_dashboard()
fix_backtesting()
print("Surgical repair of engine and frontend pages complete.")
