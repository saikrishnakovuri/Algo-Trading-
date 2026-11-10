import os
import re
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except Exception:
    genai = None
    GEMINI_AVAILABLE = False


class AIAnalysisLayer:
    """AI Analysis layer with optional Gemini integration and deterministic fallback.

    If GEMINI_API_KEY is configured and the library is available, queries Gemini.
    Otherwise uses a conservative local rule-based reasoning to produce a
    structured decision in the required format.
    """

    def __init__(self):
        self.gemini_enabled = False
        api_key = os.getenv("GEMINI_API_KEY")
        if GEMINI_AVAILABLE and api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.gemini_enabled = True
            except Exception:
                self.gemini_enabled = False

    @staticmethod
    def _safe_float(x, default: float = 0.0) -> float:
        """Safely coerce various scalar/Series/ndarray types to float."""
        try:
            if x is None:
                return float(default)
            if isinstance(x, (pd.Series,)):
                return float(x.iloc[0])
            if isinstance(x, (np.ndarray,)):
                return float(x.item())
            return float(x)
        except Exception:
            try:
                return float(np.array(x).item())
            except Exception:
                return float(default)

    def analyze_market(self, market_summary: str) -> str:
        """Return a decision string in the EXACT required format.

        Falls back to `local_analysis` on any error or if Gemini is disabled.
        """
        if self.gemini_enabled:
            prompt = f"""
You are an elite AI Trading Decision Validator. Your job is NOT just to explain the data, but to critically evaluate the algorithmic system's setup and find reasons why it might fail.

========================
🎯 OBJECTIVE: Validate the high-probability setup or reject it if forced.
========================

### Market Data Input:
{market_summary}

========================
🧠 VALIDATION PROCESS (EXPLAIN IN THIS EXACT ORDER):
========================

1️⃣ MARKET REGIME CHECK: Is the market Trending, Ranging, or Volatile? Does the setup match the regime?
2️⃣ ZONE QUALITY EVALUATION: Are we at a fresh, highly-tested, or decaying zone? Are we entering at the optimal boundary?
3️⃣ LIQUIDITY & TRAP THREATS: Where is the retail liquidity? Is this setup potentially a trap by smart money?
4️⃣ TIME-OF-DAY CONTEXT: Is this trade happening during a high-probability window (e.g., 9:30-11:30 or 1:45-3:00) or a low-probability chop zone?
5️⃣ OPTION CHAIN CONVICTION: Analyze the OI Build-up Type (Long buildup, Short covering, Long unwinding, Short buildup). Does it strongly confirm the direction?
6️⃣ DEVIL'S ADVOCATE (CRITICAL): List the top 2 reasons why this specific trade could FAIL.
7️⃣ FINAL AI VALIDATION DECISION: Given the above, is this a high-quality, asymmetric setup? (CE / PE / NO TRADE)

========================
⚠️ RULES: If the "Devil's Advocate" reasons are too strong, you MUST reject the trade (NO TRADE). Never force a trade.
========================

### Required Output Format (STRICT):
(Follow the 7 steps above exactly)

Trade: CE / PE / NO TRADE
Confidence: XX%
Reason: (Short summary of validation & threats)
Entry: value
Stop Loss: value
Target 1: value
Target 2: value
"""
            try:
                resp = self.model.generate_content(prompt)
                # Some SDKs return text attr, some return object — handle both
                text = getattr(resp, "text", None) or str(resp)
                if not text or "Trade:" not in text:
                    return self.local_analysis(market_summary)
                return text
            except Exception:
                return self.local_analysis(market_summary)

        return self.local_analysis(market_summary)

    def local_analysis(self, market_summary: str) -> str:
        """Deterministic fallback that constructs a strict-format decision.

        The logic is conservative and explainable — it will often return
        `NO TRADE` unless multiple confirming signals align.
        """
        # Extract numeric fields
        def extract_float(pattern, default=None):
            m = re.search(pattern, market_summary)
            if not m:
                return default
            try:
                return self._safe_float(m.group(1), default=default)
            except Exception:
                return default

        price = extract_float(r"Current Price:\s*([0-9]+\.?[0-9]*)")
        rsi = extract_float(r"RSI:\s*([0-9]+\.?[0-9]*)")
        trend = None
        m = re.search(r"Trend Direction:\s*([A-Za-z]+)", market_summary)
        if m:
            trend = m.group(1)

        price_action = ""
        m = re.search(r"Price Action:\s*(.*)", market_summary)
        if m:
            price_action = m.group(1)

        option_ce = ""
        if "CE OI" in market_summary:
            m = re.search(r"CE OI:\s*(.*)", market_summary)
            if m:
                option_ce = m.group(1)

        # Heuristic scoring
        score = 50
        reasons = []

        if trend and trend.lower().startswith("up"):
            score += 10
            reasons.append("EMA trend indicates uptrend")
        elif trend and trend.lower().startswith("down"):
            score -= 10
            reasons.append("EMA trend indicates downtrend")

        if price_action and "Bullish" in price_action:
            score += 15
            reasons.append("Recent bullish price action / breakout")
        if price_action and "Bearish" in price_action:
            score -= 15
            reasons.append("Recent bearish price action")

        if rsi is not None:
            if 40 <= rsi <= 70:
                score += 10
                reasons.append(f"RSI at {rsi:.1f} is within momentum range")
            elif rsi > 75:
                score -= 10
                reasons.append(f"RSI at {rsi:.1f} is overbought")

        if option_ce and ("unwinding" in option_ce.lower() or "unwind" in option_ce.lower()):
            score += 10
            reasons.append("Option chain: CE OI unwinding (short covering / rollover)")

        # Final decision
        confidence = max(0, min(95, score))

        # Default NO TRADE
        if confidence < 65:
            reason_text = "; ".join(reasons) if reasons else "No strong confirming signals"
            return (
                "Trade: NO TRADE\n"
                f"Confidence: {int(confidence)}%\n"
                f"Reason: {reason_text}\n"
                "Entry: -\n"
                "Stop Loss: -\n"
                "Target 1: -\n"
                "Target 2: -\n"
            )

        # Build CE/PE trade depending on direction
        trade_type = "CE" if (trend and trend.lower().startswith("up")) or ("Bullish" in price_action) else "PE"

        # Safe numeric defaults if price missing
        if price is None:
            price = 100.0

        # Stop loss logic: use support if present, otherwise a small percent
        support = None
        m = re.search(r"Support:\s*([0-9]+\.?[0-9]*)", market_summary)
        if m:
            try:
                support = self._safe_float(m.group(1))
            except Exception:
                support = None

        if trade_type == "CE":
            if support and support < price:
                sl = support - max(1.0, 0.001 * price)
            else:
                sl = price - max(1.0, 0.003 * price)
            dist = price - sl if price > sl else max(1.0, 0.003 * price)
            t1 = price + 2 * dist
            t2 = price + 3 * dist
        else:
            # PE
            resistance = None
            m = re.search(r"Resistance:\s*([0-9]+\.?[0-9]*)", market_summary)
            if m:
                try:
                    resistance = self._safe_float(m.group(1))
                except Exception:
                    resistance = None
            if resistance and resistance > price:
                sl = resistance + max(1.0, 0.001 * price)
            else:
                sl = price + max(1.0, 0.003 * price)
            dist = sl - price if sl > price else max(1.0, 0.003 * price)
            t1 = price - 2 * dist
            t2 = price - 3 * dist

        reason_text = "; ".join(reasons)

        return (
            f"Trade: {trade_type}\n"
            f"Confidence: {int(confidence)}%\n"
            f"Reason: {reason_text}\n"
            f"Entry: {price:.2f}\n"
            f"Stop Loss: {sl:.2f}\n"
            f"Target 1: {t1:.2f}\n"
            f"Target 2: {t2:.2f}\n"
        )

