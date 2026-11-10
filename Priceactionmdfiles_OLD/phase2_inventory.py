import json
import os
import re
import datetime
import glob

def extract_tabs(app_jsx_path):
    tabs = []
    if not os.path.exists(app_jsx_path): return tabs
    content = open(app_jsx_path, "r", encoding="utf-8").read()
    
    # Simple regex for Route components
    pattern = r'<Route\s+path=["\'](.*?)["\'].*?element=\{<(.*?)\s*/>\}'
    matches = re.finditer(pattern, content)
    for match in matches:
        tabs.append({
            "name": match.group(2),
            "route": match.group(1),
            "component": f"{match.group(2)}.jsx"
        })
    return tabs

def extract_ui_elements_and_apis(components_dir, pages_dir):
    ui_elements = []
    api_calls_used = []
    
    # Process both components and pages
    all_files = []
    if os.path.exists(components_dir):
        all_files.extend(glob.glob(f"{components_dir}/**/*.jsx", recursive=True))
        all_files.extend(glob.glob(f"{components_dir}/**/*.js", recursive=True))
    if os.path.exists(pages_dir):
        all_files.extend(glob.glob(f"{pages_dir}/**/*.jsx", recursive=True))
        all_files.extend(glob.glob(f"{pages_dir}/**/*.js", recursive=True))
        
    for file in all_files:
        try:
            content = open(file, "r", encoding="utf-8").read()
            comp_name = os.path.basename(file).split('.')[0]
            
            # Find fetch calls
            api_pattern = r'fetch\([`"\'](.*?)[`"\']'
            matches = re.finditer(api_pattern, content)
            for match in matches:
                url = match.group(1)
                if url.startswith("${API_BASE}"):
                    url = url.replace("${API_BASE}", "/api")
                elif url.startswith("${API_BASE}"):
                    url = url.replace("${API_BASE}", "/api")
                if url not in api_calls_used:
                    api_calls_used.append(url)
                    
            # Find axios/api.xxx calls
            axios_pattern = r'(?:api|axios)\.(get|post|put|delete)\([`"\'](.*?)[`"\']'
            matches = re.finditer(axios_pattern, content)
            for match in matches:
                method = match.group(1).upper()
                url = match.group(2)
                api_calls_used.append(f"{method} {url}")
                
            # Find buttons
            button_pattern = r'<button.*?>(.*?)</button>'
            matches = re.finditer(button_pattern, content, re.DOTALL)
            for match in matches:
                label = re.sub(r'<.*?>', '', match.group(1)).strip()
                if label:
                    ui_elements.append({
                        "tab": comp_name,
                        "element_type": "button",
                        "label": label[:50],
                        "interactive": True
                    })
                    
            # Find inputs
            input_pattern = r'<input.*?>|<select.*?>.*?</select>'
            matches = re.finditer(input_pattern, content, re.DOTALL)
            for match in matches:
                ui_elements.append({
                    "tab": comp_name,
                    "element_type": "form_input",
                    "interactive": True
                })
        except Exception as e:
            print(f"Error parsing {file}: {e}")
            
    # Clean API calls (remove duplicates)
    api_calls_used = list(set(api_calls_used))
    return ui_elements, api_calls_used

def main():
    root = ".."
    frontend_src = os.path.join(root, "AlgoTradingTelegramBotAndFrontend", "frontend", "src")
    
    app_jsx = os.path.join(frontend_src, "App.js") # It was App.js based on previous context
    if not os.path.exists(app_jsx):
        app_jsx = os.path.join(frontend_src, "App.jsx")
        
    tabs = extract_tabs(app_jsx)
    
    components_dir = os.path.join(frontend_src, "components")
    pages_dir = os.path.join(frontend_src, "pages")
    
    ui_elements, api_calls_used = extract_ui_elements_and_apis(components_dir, pages_dir)
    
    # Provide placeholders for websockets and saves since we can refine this later
    inventory = {
        "phase": 2,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "tabs": tabs,
        "ui_elements": ui_elements,
        "api_calls_used": api_calls_used,
        "ws_subscriptions_used": [],
        "save_buttons_present": []
    }
    
    with open("frontend_inventory_v1.json", "w") as f:
        json.dump(inventory, f, indent=2)
        
    print("frontend_inventory_v1.json generated successfully")
    print(f"Tabs: {len(tabs)}")
    print(f"UI Elements: {len(ui_elements)}")
    print(f"API Calls Used: {len(api_calls_used)}")

if __name__ == "__main__":
    main()
