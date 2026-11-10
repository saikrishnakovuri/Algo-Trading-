import re
import pandas as pd
import numpy as np

class DecisionEngine:
    """Enforces strict trading rules on AI or rule-based outputs.

    - Requires confidence >= min_confidence (default 65)
    - Enforces RR >= 1:2
    - Returns final decision string in required strict format
    """

    def __init__(self, min_confidence=65, min_rr=2.0):
        self.min_confidence = min_confidence
        self.min_rr = min_rr

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

    def parse_ai_output(self, text: str):
        """Parse AI output text into a dict.

        Returns dict with keys: trade, confidence, reason, entry, sl, t1, t2
        Missing numeric values become None.
        """
        out = {
            "trade": None,
            "confidence": None,
            "reason": None,
            "entry": None,
            "sl": None,
            "t1": None,
            "t2": None,
        }

        def find(pattern):
            m = re.search(pattern, text, re.IGNORECASE)
            return m.group(1).strip() if m else None

        out['trade'] = find(r"Trade:\s*([^\n]+)")
        conf = find(r"Confidence:\s*([0-9]+)\%?")
        out['confidence'] = int(conf) if conf and conf.isdigit() else None
        out['reason'] = find(r"Reason:\s*(.+)")

        def num(field):
            v = find(rf"{field}:\s*([0-9]+\.?[0-9]*)")
            try:
                if v is None: return None
                return self._safe_float(v)
            except Exception:
                return None

        out['entry'] = num('Entry')
        out['sl'] = num('Stop Loss') or num('StopLoss') or num('SL')
        out['t1'] = num('Target 1') or num('Target1')
        out['t2'] = num('Target 2') or num('Target2')

        return out


    def enforce_rules(self, parsed: dict, market_context: dict = None):
        """Apply strict filters. Returns (allowed:bool, message:str, final_parsed:dict)

        If not allowed, message will explain why.
        """
        if not parsed or parsed.get('trade') is None:
            return False, 'No trade details provided by AI', parsed

        trade = parsed['trade'].strip().upper()
        if trade == 'NO TRADE' or trade == 'NO':
            return False, 'AI recommended no trade', parsed

        conf = parsed.get('confidence') or 0
        if conf < self.min_confidence:
            return False, f'Confidence {conf}% < required {self.min_confidence}%', parsed

        entry = parsed.get('entry')
        sl = parsed.get('sl')
        t1 = parsed.get('t1')
        t2 = parsed.get('t2')

        # Need numeric entry and sl and at least one target to compute RR
        if entry is None or sl is None or (t1 is None and t2 is None):
            return False, 'Missing numeric entry/SL/targets to validate risk-reward', parsed

        # Compute RR using the closest valid target (prefer T1)
        target = t1 if t1 is not None else t2

        if trade.startswith('CE'):
            stop_dist = entry - sl
            targ_dist = target - entry
        else:
            stop_dist = sl - entry
            targ_dist = entry - target

        if stop_dist <= 0 or targ_dist <= 0:
            return False, 'Invalid entry/SL/target geometry', parsed

        rr = targ_dist / stop_dist
        if rr < self.min_rr:
            return False, f'RR {rr:.2f} < required {self.min_rr}:1', parsed

        # Additional market-context checks
        if market_context:
            trend = market_context.get('trend')
            if trend and trend.lower().startswith('side'):
                return False, 'Market is sideways', parsed

        # Passed all checks
        return True, 'Approved', parsed

    def evaluate(self, ai_text: str, market_context: dict = None) -> str:
        parsed = self.parse_ai_output(ai_text or "")
        allowed, message, parsed = self.enforce_rules(parsed, market_context)

        if not allowed:
            # Return NO TRADE formatted output with reason
            reason = parsed.get('reason') or message
            conf = parsed.get('confidence') or 0
            return (
                "Trade: NO TRADE\n"
                f"Confidence: {int(conf)}%\n"
                f"Reason: {message}; {reason}\n"
                "Entry: -\n"
                "Stop Loss: -\n"
                "Target 1: -\n"
                "Target 2: -\n"
            )

        # Approved — prepare target values
        t1_val = parsed.get('t1') if parsed.get('t1') is not None else parsed.get('t2')
        t2_val = parsed.get('t2') if parsed.get('t2') is not None else parsed.get('t1')

        t1_str = f"{t1_val:.2f}" if t1_val is not None else "-"
        t2_str = f"{t2_val:.2f}" if t2_val is not None else "-"

        return (
            f"Trade: {parsed['trade'].strip()}\n"
            f"Confidence: {int(parsed['confidence'])}%\n"
            f"Reason: {parsed.get('reason') or 'Approved by DecisionEngine'}\n"
            f"Entry: {parsed['entry']:.2f}\n"
            f"Stop Loss: {parsed['sl']:.2f}\n"
            f"Target 1: {t1_str}\n"
            f"Target 2: {t2_str}\n"
        )
