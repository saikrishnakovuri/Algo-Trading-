
import os

FRONTEND_SRC = '../AlgoTradingTelegramBotAndFrontend/frontend/src'

def fix_frontend_urls():
    files_to_fix = [
        os.path.join(FRONTEND_SRC, 'pages', 'PADashboard.js'),
        os.path.join(FRONTEND_SRC, 'pages', 'TradeJournal.js')
    ]
    
    inject_code = """
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
"""
    
    for filepath in files_to_fix:
        if not os.path.exists(filepath): continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Inject BACKEND_URL definition if not present
        if 'const BACKEND_URL' not in content:
            # Inject after imports
            content = content.replace("from 'lucide-react';", "from 'lucide-react';" + inject_code)
            
        # 2. Replace the API_BASE definitions
        content = content.replace("const API_BASE = '/api/pa';", "const API_BASE = `${BACKEND_URL}/api/pa`;")
        content = content.replace("const API_BASE = '/api/journal';", "const API_BASE = `${BACKEND_URL}/api/journal`;")
        
        # 3. Fix standard fetch calls that might be using literals
        content = content.replace("href={`${API_BASE}/export`}", "href={`${API_BASE}/export`}") # Already correct
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
    print("Successfully updated frontend components to use http://localhost:8000")

if __name__ == "__main__":
    fix_frontend_urls()
