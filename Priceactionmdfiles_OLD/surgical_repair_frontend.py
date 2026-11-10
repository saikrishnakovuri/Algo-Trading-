
import os

# Paths
dashboard_page = '../AlgoTradingTelegramBotAndFrontend/frontend/src/pages/Dashboard.jsx'
sidebar_page = '../AlgoTradingTelegramBotAndFrontend/frontend/src/components/Sidebar.jsx'
backtesting_page = '../AlgoTradingTelegramBotAndFrontend/frontend/src/pages/Backtesting.jsx'
app_page = '../AlgoTradingTelegramBotAndFrontend/frontend/src/App.js'

def fix_dashboard():
    if not os.path.exists(dashboard_page): return
    with open(dashboard_page, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Add Link import if missing
    if 'import { Link } from "react-router-dom";' not in content:
        content = content.replace("import { useApi }", 'import { Link } from "react-router-dom";\nimport { useApi }')

    # 2. Fix Quick Links (Remove emojis, use Link instead of a)
    old_links_pattern = '{/* Quick Links for Integration Visibility */}'
    # If already exists, we replace the block
    start_tag = '{/* Quick Links for Integration Visibility */}'
    end_tag = '</div>'
    
    idx = content.find(start_tag)
    if idx != -1:
        end_idx = content.find(end_tag, idx + len(start_tag))
        if end_idx != -1:
            new_links = """
      {/* Quick Links for Integration Visibility */}
      <div className="flex flex-wrap gap-4 mb-4">
        <Link to="/control-center" className="px-4 py-2 bg-[#00bcd4]/10 border border-[#00bcd4]/30 rounded-lg text-[#00bcd4] text-xs font-bold hover:bg-[#00bcd4]/20 transition-all">CONTROL CENTER</Link>
        <Link to="/pa-engine" className="px-4 py-2 bg-purple-500/10 border border-purple-500/30 rounded-lg text-purple-400 text-xs font-bold hover:bg-purple-500/20 transition-all">PA ENGINE</Link>
        <Link to="/journal" className="px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-xs font-bold hover:bg-green-500/20 transition-all">TRADE JOURNAL</Link>
        <Link to="/backtest" className="px-4 py-2 bg-orange-500/10 border border-orange-500/30 rounded-lg text-orange-400 text-xs font-bold hover:bg-orange-500/20 transition-all">RUN BACKTEST</Link>
        <Link to="/config-explorer" className="px-4 py-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400 text-xs font-bold hover:bg-blue-500/20 transition-all">CONFIG EXPLORER</Link>
      </div>"""
            content = content[:idx] + new_links + content[end_idx + len(end_tag):]

    with open(dashboard_page, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_sidebar():
    if not os.path.exists(sidebar_page): return
    with open(sidebar_page, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove DEBUG_FORCE and fix any garbled text
    if '{ name: \'DEBUG_FORCE\', path: \'/debug\', icon: <Bug size={20} /> },' in content:
        content = content.replace('{ name: \'DEBUG_FORCE\', path: \'/debug\', icon: <Bug size={20} /> },', '')
    
    with open(sidebar_page, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_backtesting():
    if not os.path.exists(backtesting_page): return
    with open(backtesting_page, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ensure RefreshCw is imported
    if 'RefreshCw' not in content and 'lucide-react' in content:
        content = content.replace('Activity', 'Activity, RefreshCw')
    
    # Fix the trade row to be ultra-safe
    old_row = "<td className=\"py-2 text-gray-500\">{t.entry_time.split(' ')[0]}</td>"
    new_row = "<td className=\"py-2 text-gray-500\">{(t.entry_time || '').split(' ')[0] || (t.entry_time || '').split('T')[0]}</td>"
    content = content.replace(old_row, new_row)
    
    with open(backtesting_page, 'w', encoding='utf-8') as f:
        f.write(content)

fix_dashboard()
fix_sidebar()
fix_backtesting()
print("Surgical repair of frontend components complete.")
