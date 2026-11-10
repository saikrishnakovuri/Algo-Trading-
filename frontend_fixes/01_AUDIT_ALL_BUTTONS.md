
Action: file_editor create /app/frontend_fixes/01_AUDIT_ALL_BUTTONS.md --file-text "# 01 — AUDIT EVERY BUTTON IN THE FRONTEND
## Discover, document, and test every single interactive element

---

## MISSION

Scan the ENTIRE React frontend source code, find EVERY button, toggle, input, dropdown, link, and interactive element. Test each one. Document which work and which don't.

**Output:** `FRONTEND_AUDIT_REPORT.md` with every element catalogued.

---

## STEP 1: SCAN ALL REACT COMPONENTS

```bash
# Find all React component files
find AlgoTradingTelegramBotAndFrontend/frontend/src -name \"*.js\" -o -name \"*.jsx\" -o -name \"*.tsx\" -o -name \"*.ts\" | grep -v node_modules | sort
```

For EACH component file found:

```bash
# Extract all interactive elements
grep -n \"onClick\|onSubmit\|onChange\|onToggle\|handleClick\|handleSubmit\|handleChange\|button\|Button\|<input\|<select\|<form\|href=\|Link\|toggle\|Switch\|Checkbox\|Radio\|Dropdown\|Modal\|Tab\|disabled\" <file>
```

## STEP 2: CREATE THE AUDIT TABLE

Create `FRONTEND_AUDIT_REPORT.md`:

```markdown
# Frontend Button & Interactive Element Audit

| # | Component File | Element | Type | Label/Text | onClick Handler | API Endpoint Called | Works? | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | App.js | Login Button | button | \"Login\" | handleLogin() | POST /api/auth/login | ✅/❌ | |
| 2 | Dashboard.js | Start Bot | button | \"Start Trading\" | handleStart() | POST /api/bot/start | ✅/❌ | |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
```

## STEP 3: TEST EACH ELEMENT

For each element found:

1. **Trace the handler function** — What does `onClick` call?
2. **Trace the API call** — Does the handler call `fetch()` or `axios`? What endpoint?
3. **Check if the backend endpoint exists** — Search `server.py` for that route
4. **Check if the endpoint returns data** — `curl` the endpoint
5. **Check if the frontend handles the response** — Does it update state? Show toast?

```python
# Automated check script
import re, os

# Read all JS files
frontend_src = \"AlgoTradingTelegramBotAndFrontend/frontend/src\"
server_file = \"AlgoTradingTelegramBotAndFrontend/backend/server.py\"

# Read server routes
with open(server_file) as f:
    server_code = f.read()

# Extract all API routes from server
server_routes = set(re.findall(r'@app\.(get|post|put|delete|patch)\([\"\']([^\"\']+)', server_code))

# For each component file
for root, dirs, files in os.walk(frontend_src):
    for fname in files:
        if not fname.endswith(('.js', '.jsx', '.tsx')): continue
        filepath = os.path.join(root, fname)
        with open(filepath) as f:
            code = f.read()
        
        # Find all fetch/axios calls
        api_calls = re.findall(r'fetch\([`\"\']([^`\"\']+)', code)
        api_calls += re.findall(r'axios\.\w+\([`\"\']([^`\"\']+)', code)
        
        # Find all buttons
        buttons = re.findall(r'onClick\s*=\s*\{([^}]+)\}', code)
        
        if api_calls or buttons:
            print(f\"\n{filepath}:\")
            for api in api_calls:
                # Check if route exists in backend
                api_clean = api.replace('${API_URL}', '').replace('${BACKEND_URL}', '')
                exists = any(api_clean in route[1] for route in server_routes)
                print(f\"  API: {api_clean} — {'EXISTS' if exists else 'MISSING IN BACKEND'}\")
            for btn in buttons:
                print(f\"  Button: {btn.strip()}\")
```

## STEP 4: CATEGORIZE RESULTS

After testing, categorize each element:

```
WORKING (✅):     Elements that function correctly end-to-end
BROKEN (❌):       Elements that crash, show errors, or don't respond
DISABLED (⚫):     Elements that are grayed out or hidden
MISSING API (🔴):  Frontend calls API that doesn't exist in backend
NO HANDLER (🟡):   Button exists but onClick does nothing
PARTIAL (🟠):      Works partially (e.g., saves but doesn't refresh UI)
```

## STEP 5: SAVE THE AUDIT

Save the complete audit report with EVERY element, its status, and what needs fixing.

**This audit is the input for the next MD file (02_FIX_BROKEN_BUTTONS.md).**

## AFTER THIS, MOVE TO 02_FIX_BROKEN_BUTTONS.md. DO NOT FIX ANYTHING YET. JUST AUDIT.
"
Observation: Create successful: /app/frontend_fixes/01_AUDIT_ALL_BUTTONS.md