
import os

backtesting_page = '../AlgoTradingTelegramBotAndFrontend/frontend/src/pages/Backtesting.jsx'

def final_surgical_fix():
    if not os.path.exists(backtesting_page):
        print(f"Error: {backtesting_page} not found")
        return

    with open(backtesting_page, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix Total PnL display
    old_pnl_block = """<p className={`text-xl font-bold ${result.metrics.total_pnl >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'}`}>â‚¹{result.metrics.total_pnl?.toLocaleString()}</p>"""
    # Note: encoding might be different in the actual file, using simpler match
    
    # Let's find the pnl line specifically
    import re
    pnl_pattern = re.compile(r'<p className={`text-xl font-bold \$\{result\.metrics\.total_pnl >= 0 \? \'text-\[#00c853\]\' : \'text-\[#ff1744\]\'\}`}>.*?\{result\.metrics\.total_pnl\?\.toLocaleString\(\)\}</p>')
    
    new_pnl_line = """<p className={`text-xl font-bold ${(result?.metrics?.total_pnl || 0) >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'}`}>â‚¹{(result?.metrics?.total_pnl || 0).toLocaleString()}</p>"""
    
    # 2. Fix trade table numeric fields
    # Entry Price
    content = content.replace('{t.entry_price.toFixed(1)}', '{(t.entry_price || 0).toFixed(1)}')
    # Exit Price
    content = content.replace('{t.exit_price.toFixed(1)}', '{(t.exit_price || 0).toFixed(1)}')
    # Net PnL comparison
    content = content.replace('${t.net_pnl >= 0', '${(t.net_pnl || 0) >= 0')
    # Net PnL value display
    content = content.replace('{t.net_pnl >= 0 ? \'+\' : \'\'}{t.net_pnl.toFixed(0)}', '{(t.net_pnl || 0) >= 0 ? \'+\' : \'\'}{(t.net_pnl || 0).toFixed(0)}')

    # Since regex on complex JSX can be tricky with exact spacing/encoding, let's use a more robust replacement for the PnL block
    
    old_pnl_fragment = "result.metrics.total_pnl >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'"
    new_pnl_fragment = "(result?.metrics?.total_pnl || 0) >= 0 ? 'text-[#00c853]' : 'text-[#ff1744]'"
    content = content.replace(old_pnl_fragment, new_pnl_fragment)
    
    old_pnl_display = "{result.metrics.total_pnl?.toLocaleString()}"
    new_pnl_display = "{(result?.metrics?.total_pnl || 0).toLocaleString()}"
    content = content.replace(old_pnl_display, new_pnl_display)

    with open(backtesting_page, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Surgical fix for Backtesting.jsx applied.")

if __name__ == "__main__":
    final_surgical_fix()
