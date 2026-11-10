
import re
import os
import json

FRONTEND_SRC = "../AlgoTradingTelegramBotAndFrontend/frontend/src"
SERVER_FILE = "../AlgoTradingTelegramBotAndFrontend/backend/server.py"

def run_audit():
    # 1. Read server routes
    if not os.path.exists(SERVER_FILE):
        print(f"Error: {SERVER_FILE} not found")
        return
        
    with open(SERVER_FILE, 'r', encoding='utf-8') as f:
        server_code = f.read()

    # Extract all API routes from server
    # e.g. @app.get("/api/pa/config") -> ('get', '/api/pa/config')
    server_routes = re.findall(r'@app\.(get|post|put|delete|patch)\([\"\']([^\"\']+)', server_code)
    # Also find routes from api_router
    # e.g. @api_router.post("/bot/{event_type}") -> ('post', '/bot/{event_type}')
    server_routes += re.findall(r'@api_router\.(get|post|put|delete|patch)\([\"\']([^\"\']+)', server_code)
    
    # Normalize routes for lookup (ignoring params like {job_id})
    normalized_routes = []
    for method, path in server_routes:
        # Replace {param} with [^/]+
        regex_path = re.sub(r'\{[^}]+\}', '[^/]+', path)
        # Handle prefix /api
        if not path.startswith('/api') and '@api_router' in server_code:
             normalized_routes.append((method.upper(), '^/api' + regex_path + '$'))
        else:
             normalized_routes.append((method.upper(), '^' + regex_path + '$'))

    audit_results = []
    
    # 2. For each component file
    for root, dirs, files in os.walk(FRONTEND_SRC):
        for fname in files:
            if not fname.endswith(('.js', '.jsx', '.tsx')): continue
            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, FRONTEND_SRC)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                code = "".join(lines)

            # Find all interactive elements
            # Extract buttons, inputs, selects, links
            # We'll search for common patterns
            
            # Simple line-by-line grep-like search for report
            for i, line in enumerate(lines):
                ln = i + 1
                if any(x in line for x in ["onClick", "onSubmit", "onChange", "<button", "<input", "<select", "Link to="]):
                    # Extract approximate element info
                    type_str = "Unknown"
                    if "<button" in line: type_str = "button"
                    elif "<input" in line: type_str = "input"
                    elif "<select" in line: type_str = "select"
                    elif "Link to=" in line: type_str = "link"
                    elif "onClick" in line: type_str = "event-handler"
                    
                    label = "N/A"
                    label_match = re.search(r'>([^<]+)</', line)
                    if label_match: label = label_match.group(1).strip()
                    
                    handler = "N/A"
                    handler_match = re.search(r'onClick\s*=\s*\{([^}]+)\}', line)
                    if handler_match: handler = handler_match.group(1).strip()
                    
                    # Trace API call in the file if handler exists
                    api_call = "None detected"
                    if handler != "N/A":
                        # Look for function definition
                        func_name = handler.split('(')[0]
                        # Find fetch or axios calls within this file that might be related
                        # This is a bit heuristic
                        api_match = re.search(r'fetch\([`\"\']([^`\"\']+)', code)
                        if api_match: api_call = api_match.group(1)
                    
                    works = "CHECK"
                    notes = ""
                    
                    # Cross-reference api_call with server_routes
                    if api_call != "None detected":
                         # Heuristic matching
                         clean_api = api_call.replace('${API_URL}', '').replace('${BACKEND_URL}', '').replace('http://localhost:8000', '')
                         if not clean_api.startswith('/'): clean_api = '/' + clean_api
                         
                         found = False
                         for method, r_regex in normalized_routes:
                             if re.search(r_regex, clean_api):
                                 found = True
                                 break
                         if found:
                             works = "✅"
                             notes = f"Matched API: {clean_api}"
                         else:
                             works = "🔴"
                             notes = f"API MISMATCH: {clean_api} not found in server.py"

                    audit_results.append({
                        "file": rel_path,
                        "line": ln,
                        "type": type_str,
                        "label": label,
                        "handler": handler,
                        "api": api_call,
                        "works": works,
                        "notes": notes
                    })

    # Generate Markdown Report
    report = "# Frontend Button & Interactive Element Audit\n\n"
    report += "| # | Component File | Line | Type | Label/Text | onClick Handler | API Endpoint | Works? | Notes |\n"
    report += "|---|---|---|---|---|---|---|---|---|\n"
    
    for i, item in enumerate(audit_results, 1):
        report += f"| {i} | {item['file']} | {item['line']} | {item['type']} | \"{item['label']}\" | `{item['handler']}` | `{item['api']}` | {item['works']} | {item['notes']} |\n"
    
    with open("FRONTEND_AUDIT_REPORT.md", "w", encoding='utf-8') as f:
        f.write(report)
    
    print(f"Audit complete. {len(audit_results)} elements catalogued in FRONTEND_AUDIT_REPORT.md")

if __name__ == "__main__":
    run_audit()
