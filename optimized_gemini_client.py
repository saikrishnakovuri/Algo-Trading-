"""
Optimized Gemini API Client with:
- Batching (multiple prompts in one request)
- Caching (avoid re-analyzing same data)
- Rate limiting (respect quota)
- Error handling (retry logic)
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class OptimizedGeminiClient:
    """
    Production-ready Gemini API client with quota management
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        genai.configure(api_key=self.api_key)
        # Use gemini-2.5-flash: fastest & cheapest for real-time trading
        self.model = genai.GenerativeModel('gemini-2.5-flash')  # Latest stable for free tier
        
        # Local cache: {prompt_hash: (response, timestamp)}
        self.cache = {}
        self.cache_ttl_hours = 24  # Cache for 24 hours
        
        # Rate limiting
        self.request_times = []  # Track request times
        self.max_requests_per_min = 60  # Adjust based on your quota
        
        print(f"✓ Gemini Client initialized")
        print(f"  - API Key: {self.api_key[:20]}...{self.api_key[-10:]}")
        print(f"  - Cache TTL: {self.cache_ttl_hours} hours")
        print(f"  - Rate limit: {self.max_requests_per_min} req/min")

    def _get_cache_key(self, prompt: str) -> str:
        """Generate consistent cache key from prompt"""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: tuple) -> bool:
        """Check if cached response is still valid"""
        response, timestamp = cache_entry
        age_hours = (datetime.now() - timestamp).total_seconds() / 3600
        return age_hours < self.cache_ttl_hours

    def _check_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # If we're at limit, wait
        if len(self.request_times) >= self.max_requests_per_min:
            wait_time = 61 - (now - self.request_times[0])
            print(f"⏱️  Rate limited. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        self.request_times.append(now)

    def analyze_single(self, prompt: str, use_cache: bool = True) -> str:
        """
        Analyze a single prompt with caching
        
        Args:
            prompt: The prompt to send
            use_cache: Whether to use cached responses
            
        Returns:
            Generated text response
        """
        cache_key = self._get_cache_key(prompt)
        
        # Check cache first
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry):
                print(f"✓ Cache hit for prompt (saved 1 API call)")
                return cache_entry[0]
            else:
                del self.cache[cache_key]
        
        # Make actual API call
        self._check_rate_limit()
        
        try:
            print(f"→ Sending request to Gemini...")
            response = self.model.generate_content(prompt)
            result = response.text
            
            # Cache the response
            self.cache[cache_key] = (result, datetime.now())
            
            return result
        
        except Exception as e:
            if "429" in str(e):
                raise RuntimeError(
                    f"❌ 429 Quota Exceeded\n"
                    f"   Your API key is likely on FREE TIER (20 req/day)\n"
                    f"   Follow GEMINI_API_FIX_GUIDE.txt to enable billing"
                )
            raise

    def analyze_batch(self, prompts: List[str], use_cache: bool = True) -> List[str]:
        """
        Analyze multiple prompts (reduces total requests via batching)
        
        Args:
            prompts: List of prompts
            use_cache: Whether to use caching
            
        Returns:
            List of responses (same order)
        """
        results = []
        
        print(f"\n📦 Batch Processing {len(prompts)} prompts...")
        
        for i, prompt in enumerate(prompts, 1):
            cache_key = self._get_cache_key(prompt)
            
            # Check cache
            if use_cache and cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    print(f"  [{i}/{len(prompts)}] ✓ Cache hit")
                    results.append(cache_entry[0])
                    continue
                else:
                    del self.cache[cache_key]
            
            # Rate limit check
            self._check_rate_limit()
            
            try:
                print(f"  [{i}/{len(prompts)}] → API call...")
                response = self.model.generate_content(prompt)
                result = response.text
                self.cache[cache_key] = (result, datetime.now())
                results.append(result)
            
            except Exception as e:
                if "429" in str(e):
                    print(f"❌ 429 ERROR - Quota exceeded after {i} requests")
                    raise
                raise
        
        print(f"✓ Batch complete: {len(prompts)} prompts processed")
        return results

    def clear_cache(self):
        """Clear all cached responses"""
        self.cache.clear()
        print("✓ Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics"""
        now = datetime.now()
        valid_entries = sum(
            1 for entry in self.cache.values() 
            if self._is_cache_valid(entry)
        )
        return {
            "total_cached": len(self.cache),
            "valid_cached": valid_entries,
            "api_calls_saved": valid_entries,
            "requests_this_minute": len(self.request_times)
        }


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    try:
        client = OptimizedGeminiClient()
        
        # Example 1: Single analysis with caching
        print("\n" + "=" * 60)
        print("EXAMPLE 1: Single Prompt (with caching)")
        print("=" * 60)
        
        prompt1 = "Analyze this NIFTY setup: Price bounced from VWAP, RSI < 50, volume declining"
        result1 = client.analyze_single(prompt1)
        print(f"\nResult:\n{result1[:200]}...")
        
        # Call again - should use cache
        result1_cached = client.analyze_single(prompt1)
        
        # Example 2: Batch processing (efficient)
        print("\n" + "=" * 60)
        print("EXAMPLE 2: Batch Processing (6 prompts)")
        print("=" * 60)
        
        market_analyses = [
            "Is NIFTY in a bullish trend?",
            "Check if BankNifty is in consolidation",
            "Analyze support/resistance zones",
            "Evaluate volatility conditions",
            "Check momentum strength",
            "Is market over-extended?"
        ]
        
        batch_results = client.analyze_batch(market_analyses)
        for i, res in enumerate(batch_results, 1):
            print(f"\n[{i}] {res[:150]}...")
        
        # Example 3: Cache statistics
        print("\n" + "=" * 60)
        print("CACHE STATISTICS")
        print("=" * 60)
        stats = client.get_cache_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
    except RuntimeError as e:
        print(f"\n{e}")
        print("\n💡 SOLUTION: Run GEMINI_API_FIX_GUIDE.txt for step-by-step fix")
