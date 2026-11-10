"""
Check what models are available for your API key
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ No API key found")
    exit(1)

genai.configure(api_key=api_key)

print("=" * 60)
print("AVAILABLE MODELS FOR YOUR API KEY")
print("=" * 60)

try:
    models = genai.list_models()
    
    print(f"\nFound {len(list(models))} models:\n")
    
    for model in genai.list_models():
        print(f"Name: {model.name}")
        print(f"  Supported methods: {model.supported_generation_methods}")
        print(f"  Display name: {model.display_name}")
        print()
        
except Exception as e:
    print(f"❌ Error: {e}")
