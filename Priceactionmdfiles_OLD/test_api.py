
import requests
import json

BASE_URL = "http://localhost:8000/api"

def check_endpoint(name, method, endpoint, payload=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, data=json.dumps(payload or {}), headers=headers)
        elif method == "PUT":
            response = requests.put(url, data=json.dumps(payload or {}), headers=headers)
        
        status = "✅" if response.status_code == 200 else "🔴"
        print(f"{status} {name:<25} | {method} {endpoint:<30} | Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error detail: {response.text[:200]}")
    except Exception as e:
        print(f"🔴 {name:<25} | {method} {endpoint:<30} | Error: {e}")

def run_full_audit():
    print("="*80)
    print("  BACKEND API AUDIT — VERIFYING ALL BUTTONS/WIRING")
    print("="*80)
    
    # Core Controls
    check_endpoint("Live Status", "GET", "/live/status")
    check_endpoint("Backtest Run", "POST", "/backtest/run", {"capital": 500000, "stocks": ["NIFTY"]})
    check_endpoint("Backtest History", "GET", "/backtest/history")
    
    # PA Engine Integration
    check_endpoint("PA Config Get", "GET", "/pa/config")
    check_endpoint("PA Strategies Get", "GET", "/pa/strategies")
    check_endpoint("PA Edge Monitor", "GET", "/pa/edge")
    check_endpoint("PA Monte Carlo", "GET", "/pa/montecarlo")
    
    # Journal
    check_endpoint("Journal Summary", "GET", "/journal/summary")
    check_endpoint("Journal Trades", "GET", "/journal/trades")
    check_endpoint("Loss Analysis", "GET", "/journal/losses/analysis")
    
    # Write a test config save
    check_endpoint("PA Config Save", "PUT", "/pa/config", {"capital": 500000, "risk_pct": 0.01})
    
    print("="*80)

if __name__ == "__main__":
    run_full_audit()
