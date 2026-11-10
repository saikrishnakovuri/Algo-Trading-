
Action: file_editor create /app/frontend_fixes/02_FIX_BROKEN_BUTTONS.md --file-text "# 02 — FIX EVERY BROKEN BUTTON
## Read the audit report, fix each broken element one by one

---

## MISSION

Read `FRONTEND_AUDIT_REPORT.md` from the previous step. For EVERY element marked ❌, 🔴, 🟡, or 🟠 — fix it.

**RULE: DO NOT CHANGE ANY EXISTING LOGIC. Only fix wiring, missing endpoints, broken handlers, and UI state issues.**

---

## FIX CATEGORIES

### Category 1: MISSING API (🔴) — Backend endpoint doesn't exist

**Fix pattern:** Add the missing route to `server.py`

```python
# In AlgoTradingTelegramBotAndFrontend/backend/server.py
# APPEND new route (don't modify existing routes)

@app.post(\"/api/missing-endpoint\")
async def missing_endpoint(request: Request):
    data = await request.json()
    # Implement the minimal logic the frontend expects
    # Read from existing data sources (files, DB, modules)
    return {\"status\": \"ok\", \"data\": result}
```

### Category 2: NO HANDLER (🟡) — Button has no onClick

**Fix pattern:** Add the handler function in the React component

```javascript
// In the component file, add the missing handler
const handleMissingAction = async () => {
    try {
        const response = await fetch(`${API_URL}/api/endpoint`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        // Update state
        setData(result);
        toast.success('Action completed');
    } catch (err) {
        toast.error('Failed: ' + err.message);
    }
};

// Connect it to the button
<button onClick={handleMissingAction}>Button Text</button>
```

### Category 3: BROKEN (❌) — Handler crashes or API returns error

**Fix pattern:** Debug the specific error

```
1. Check browser console for the error
2. If API returns 500 → fix backend route (missing import, wrong data format)
3. If API returns 404 → route doesn't exist (Category 1 fix)
4. If API returns 422 → request body format wrong (fix frontend payload)
5. If frontend crashes → null check missing, state not initialized
```

### Category 4: DISABLED (⚫) — Element is hidden or grayed out

**Fix pattern:** Find the condition that disables it and enable it

```javascript
// FIND this pattern:
<button disabled={someCondition}>

// If the condition is wrong or too restrictive, fix it:
// DON'T remove the condition entirely — understand WHY it's disabled first
// If it's disabled because of a missing feature, implement the feature
```

### Category 5: PARTIAL (🟠) — Works but doesn't update UI

**Fix pattern:** Add state refresh after the API call

```javascript
const handleAction = async () => {
    const response = await fetch(`${API_URL}/api/endpoint`, { method: 'POST' });
    const result = await response.json();
    
    // ADD THIS: Refresh the data that the UI displays
    fetchLatestData();  // or setState(result.data)
    
    // ADD THIS: Show feedback
    toast.success('Done!');
};
```

---

## EXECUTION PROCESS

For EACH broken element in the audit:

```
1. Open the component file
2. Find the element (by line number from audit)
3. Identify which category the fix falls into
4. Apply the minimal fix
5. Test: Does the button now work end-to-end?
6. If yes → mark as fixed in FRONTEND_AUDIT_REPORT.md
7. If no → investigate deeper, check console logs
8. Move to next broken element
```

---

## AFTER FIXING: RE-RUN THE AUDIT

After all fixes:
1. Start the frontend and backend
2. Click EVERY button again
3. Update `FRONTEND_AUDIT_REPORT.md` with new statuses
4. If any are still broken, fix them
5. Repeat until ALL elements are ✅

**THEN MOVE TO 03_ENABLE_CONFIG_CONTROLS.md.**
"
Observation: Create successful: /app/frontend_fixes/02_FIX_BROKEN_BUTTONS.md