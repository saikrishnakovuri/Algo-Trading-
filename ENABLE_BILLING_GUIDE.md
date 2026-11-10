═══════════════════════════════════════════════════════════════
ENABLE BILLING FOR UNLIMITED GEMINI QUOTA
═══════════════════════════════════════════════════════════════

## STEP-BY-STEP: Upgrade to Billing

1. Go to Google Cloud Console:
   https://console.cloud.google.com/

2. At top-left, click your PROJECT NAME dropdown

3. Look for your API project (check which one has your API key)

4. In left menu, click "Billing"

5. Click "Create Billing Account" or "Link Billing Account"

6. Fill in payment details:
   - Billing account name (e.g., "AlgoTrading")
   - Country: India
   - Add credit/debit card
   - Accept terms

7. Google gives you $300 free credit for new projects

8. Link the billing account to your project

9. Wait 5-10 minutes for quotas to update

10. Test:
    python debug_gemini_api.py
    → Should now work with higher quota

═══════════════════════════════════════════════════════════════
## QUOTA LIMITS AFTER BILLING
═══════════════════════════════════════════════════════════════

gemini-2.5-flash (After Billing Enabled):
✅ Requests per day: 1,000+
✅ Requests per minute: 200+
✅ Input tokens per day: 1,000,000+
✅ Practically unlimited for trading

Cost Example:
- 100 API calls = ~₹0.50 (extremely cheap)
- 1000 API calls = ~₹5 (still very cheap)

═══════════════════════════════════════════════════════════════
## VERIFY BILLING IS ENABLED
═══════════════════════════════════════════════════════════════

1. Go to: https://console.cloud.google.com/
2. Look at top-right → Your project name
3. You should see: "Billing: ENABLED" (not "DISABLED")

If it says "DISABLED":
- Click on it
- Link a billing account
- Wait 10 minutes

═══════════════════════════════════════════════════════════════
## AFTER ENABLING - USE QUOTA ENDPOINT
═══════════════════════════════════════════════════════════════

You can also upgrade to higher-tier models when billing is enabled:

✅ Can use: gemini-2.5-pro (more accurate)
✅ Can use: gemini-3-pro-preview (latest)
✅ Can use: gemini-3.1-pro-preview (cutting edge)

Current setup works great with billing:
- gemini-2.5-flash ← KEEP THIS (fast + cheap + sufficient)

═══════════════════════════════════════════════════════════════
## ESTIMATED COSTS FOR TRADING BOT
═══════════════════════════════════════════════════════════════

For a trading bot making:
- 100 market analysis calls/day
- 50 signal confirmation calls/day
- 20 risk analysis calls/day

Total: ~170 calls/day on gemini-2.5-flash

Cost: ~₹0.85/day (less than ₹1 per day!)

With $300 free credit:
- Can run for ~4 years for free! 🎉

═══════════════════════════════════════════════════════════════
## SUMMARY
═══════════════════════════════════════════════════════════════

Current:  FREE TIER → 20 req/day limit
Goal:     PAID TIER → 1000+ req/day (unlimited practically)

Action:   Enable billing (2 minutes)
Result:   Infinite quota for your trading bot
Cost:     ~₹0.50-1 per day

👉 Enable billing NOW and you're done!
═══════════════════════════════════════════════════════════════
