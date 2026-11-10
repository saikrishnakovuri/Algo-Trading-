"""
Complete diagnostics to identify exactly what's causing 429 errors
Run this to get a detailed report
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

print("\n" + "=" * 70)
print("GEMINI API 429 ERROR - COMPLETE DIAGNOSTICS")
print("=" * 70)

# ============================================================
# 1. Check Environment Configuration
# ============================================================

print("\n[CHECK 1] Environment Configuration")
print("-" * 70)

root_dir = Path(__file__).parent
backend_dir = root_dir / "AlgoTradingTelegramBotAndFrontend" / "backend"

env_files = {
    "Root .env": root_dir / ".env",
    "Backend .env": backend_dir / ".env"
}

env_configs = {}

for name, path in env_files.items():
    if path.exists():
        print(f"✓ {name}: Found at {path}")
        load_dotenv(path)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            print(f"  - GEMINI_API_KEY: {api_key[:20]}...{api_key[-10:]} (exists)")
            env_configs[name] = api_key
        else:
            print(f"  - GEMINI_API_KEY: NOT SET")
    else:
        print(f"✗ {name}: NOT FOUND at {path}")

if not env_configs:
    print("\n❌ CRITICAL: No GEMINI_API_KEY found in any .env file!")
    sys.exit(1)


# ============================================================
# 2. Check for Duplicate/Inconsistent Keys
# ============================================================

print("\n[CHECK 2] API Key Consistency")
print("-" * 70)

unique_keys = set(env_configs.values())

if len(unique_keys) == 1:
    print(f"✓ All .env files use the SAME API key (consistent)")
    api_key = list(unique_keys)[0]
elif len(unique_keys) > 1:
    print(f"⚠️  WARNING: Different API keys found across .env files!")
    print(f"  This could cause confusion. Use the same key everywhere.")
    for name, key in env_configs.items():
        print(f"  - {name}: {key[:20]}...{key[-10:]}")
    api_key = list(unique_keys)[0]  # Use first one
else:
    print(f"✗ No valid API key found")
    sys.exit(1)


# ============================================================
# 3. Test API Connection
# ============================================================

print("\n[CHECK 3] API Connection Test")
print("-" * 70)

try:
    import google.generativeai as genai
    
    print(f"✓ google-generativeai library: Installed")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    print(f"✓ API configuration: Success")
    
    # Try a simple request
    print(f"  Testing request (may show quota error)...")
    response = model.generate_content("Say 'OK'")
    print(f"✓ API request: SUCCESS")
    print(f"  Response: {response.text[:50]}...")
    
except ImportError:
    print(f"✗ google-generativeai library: NOT installed")
    print(f"  Fix: pip install google-generativeai")
    
except Exception as e:
    error_str = str(e)
    print(f"✗ API request: FAILED")
    
    if "429" in error_str or "quota" in error_str.lower():
        print(f"\n🔴 DIAGNOSIS: FREE TIER QUOTA EXCEEDED")
        print(f"   - Your API key is on a free-tier project")
        print(f"   - Limit: 20 requests/day")
        print(f"   - You need: Billing-enabled project")
        
    elif "API_KEY" in error_str or "key" in error_str.lower():
        print(f"\n🔴 DIAGNOSIS: Invalid API key")
        print(f"   - Key: {api_key[:20]}...{api_key[-10:]}")
        print(f"   - Error: {error_str}")
        
    else:
        print(f"\n⚠️  Other error: {error_str}")


# ============================================================
# 4. Check Code for Multiple Unoptimized Calls
# ============================================================

print("\n[CHECK 4] Code Review for Unnecessary API Calls")
print("-" * 70)

# Search for repeated genai calls
files_to_check = [
    root_dir / "main.py",
    root_dir / "live_options_trader.py",
    backend_dir / "server.py",
    root_dir / "modules" / "ai_analysis.py"
]

call_count = 0
for file_path in files_to_check:
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Count potential API calls
            genai_calls = content.count("model.generate_content")
            
            if genai_calls > 0:
                print(f"⚠️  {file_path.name}: {genai_calls} generate_content() calls")
                call_count += genai_calls
        except:
            pass

if call_count > 10:
    print(f"\n🔴 ALERT: {call_count} potential API calls found in code")
    print(f"   Each call uses quota. Without caching, this causes 429 errors quickly.")
    print(f"   Solution: Use optimized_gemini_client.py with caching")
else:
    print(f"✓ Reasonable number of API calls ({call_count})")


# ============================================================
# 5. Check if Optimized Client is Being Used
# ============================================================

print("\n[CHECK 5] Optimized Client Usage")
print("-" * 70)

optimized_file = root_dir / "optimized_gemini_client.py"

if optimized_file.exists():
    print(f"✓ optimized_gemini_client.py: EXISTS")
    
    # Check if it's imported anywhere
    uses_optimized = 0
    for file_path in files_to_check:
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    if "OptimizedGeminiClient" in f.read():
                        print(f"  ✓ Used in {file_path.name}")
                        uses_optimized += 1
            except:
                pass
    
    if uses_optimized == 0:
        print(f"  ⚠️  NOT imported anywhere yet")
        print(f"  Action: Update server.py and live_options_trader.py to use it")
    
else:
    print(f"✗ optimized_gemini_client.py: NOT FOUND")
    print(f"  This file should exist at: {optimized_file}")
    print(f"  It provides caching and rate limiting to prevent 429 errors")


# ============================================================
# SUMMARY & RECOMMENDATIONS
# ============================================================

print("\n" + "=" * 70)
print("SUMMARY & ACTION PLAN")
print("=" * 70)

recommendations = []

if "429" in str(e) if 'e' in locals() else False:
    recommendations.append({
        "priority": "CRITICAL",
        "action": "Enable billing on your Google Cloud project",
        "steps": [
            "Go to: https://aistudio.google.com/app/apikeys",
            "Create new API key → 'Create in new project'",
            "Update GEMINI_API_KEY in both .env files",
            "Test with: python debug_gemini_api.py"
        ]
    })

if call_count > 10:
    recommendations.append({
        "priority": "HIGH",
        "action": "Implement caching to reduce API calls",
        "steps": [
            "Use: optimized_gemini_client.py",
            "Update server.py to use OptimizedGeminiClient",
            "Update live_options_trader.py to use OptimizedGeminiClient",
            "Batch similar prompts together"
        ]
    })

recommendations.append({
    "priority": "MEDIUM",
    "action": "Monitor quota usage",
    "steps": [
        "Check: https://console.cloud.google.com/quotas",
        "Search: 'Generative Language API'",
        "Verify daily limit shows 1000+ not 20",
        "Set up alerts if quota dropping fast"
    ]
})

for i, rec in enumerate(recommendations, 1):
    print(f"\n[Recommendation {i}] {rec['priority']}: {rec['action']}")
    for j, step in enumerate(rec['steps'], 1):
        print(f"  {j}. {step}")

print("\n" + "=" * 70)
print("For detailed guide, read: GEMINI_API_FIX_GUIDE.txt")
print("For integration help, read: INTEGRATION_STEPS.md")
print("=" * 70 + "\n")
