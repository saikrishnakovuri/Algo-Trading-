"""
Debug script to verify Gemini API key and quota status
"""
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("=" * 60)
print("GEMINI API KEY VERIFICATION")
print("=" * 60)

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in .env")
    sys.exit(1)

print(f"✓ API Key found: {api_key[:20]}...{api_key[-10:]}")

# Configure API
genai.configure(api_key=api_key)

print("\n" + "=" * 60)
print("TESTING API CONNECTION & QUOTA")
print("=" * 60)

try:
    # Test 1: Basic API call with correct model name
    print("\n[Test 1] Simple text generation (to check quota)...")
    # Use latest model: gemini-2.5-flash (fastest & cheapest)
    model = genai.GenerativeModel('gemini-2.5-flash')  # Latest stable for free tier
    response = model.generate_content("Say 'Hello' in one word")
    print(f"✓ API Response: {response.text[:50]}")
    
    # Test 2: Check available models
    print("\n[Test 2] Listing available models...")
    models = genai.list_models()
    print(f"✓ Available models:")
    for m in models:
        if "gemini" in m.name.lower():
            print(f"  - {m.name} (Supports: {', '.join(m.supported_generation_methods)})")
    
    # Test 3: Check usage stats
    print("\n[Test 3] Checking usage info...")
    print("✓ Current request successful (not quota-limited YET)")
    
except Exception as e:
    error_msg = str(e)
    print(f"❌ ERROR: {error_msg}")
    
    if "429" in error_msg or "quota" in error_msg.lower():
        print("\n🔴 DIAGNOSIS: You are on FREE TIER quota (20 req/day)")
        print("   Your API key is NOT linked to a billing-enabled project")
    elif "API_KEY" in error_msg or "authenticate" in error_msg.lower():
        print("\n🔴 DIAGNOSIS: Invalid or incorrect API key")
    else:
        print(f"\n⚠️  Other error: {error_msg}")

print("\n" + "=" * 60)
print("NEXT STEPS:")
print("=" * 60)
print("""
If you got a 429 error:
1. Go to: https://aistudio.google.com/app/apikeys
2. Click 'Create API Key' → Select 'Create API key in new Google Cloud project'
3. This will create a NEW project with billing capability
4. Copy the new API key and update your .env files
5. Delete or disable the old key

If billing is not enabled:
1. Go to: https://console.cloud.google.com/billing
2. Create a billing account with valid payment method
3. Link it to the project containing your API key
""")
