
Action: file_editor create /app/INSTRUMENT_NORMALIZATION_SPEC.md --file-text "# 🔀 INSTRUMENT NORMALIZATION SPEC

> How strategy-side symbols (`NIFTY`, `BANKNIFTY`) map to adapter-side symbols (`BTCUSDT`, `EUR/USD`) — and how price/tick scales work without breaking strategy logic.

---

## 1. THE PROBLEM

Strategy code calls:
```python
df = data.get_bars(\"NIFTY\", \"5m\", 200)
price = data.get_live_price(\"NIFTY\")
```

But:
- NIFTY trades at ~25,000 (rupees, integer-ish)
- BTCUSDT trades at ~105,000 (USDT, decimal)
- EUR/USD trades at ~1.08 (USD, 4 decimals)

If strategy applies `tp_atr=1.5 * ATR` to compute target distance:
- NIFTY: ATR≈40 → tp_dist = 60 points = ₹3,900 with lot 65 ✓
- BTCUSDT: ATR≈200 → tp_dist = 300 USD ≈ ₹25,000 per coin (too big? or just fine?)
- EUR/USD: ATR≈0.0008 → tp_dist = 0.0012 = 12 pips ✓ (correct forex move)

**Strategy logic still works mathematically** because:
- ATR is computed FROM the same bars the strategy sees
- Multiplications happen in the SAME unit space
- Win/loss percentages translate identically (a 1.5R win in NIFTY = a 1.5R win in BTC, even if absolute rupees differ)

What changes:
- ABSOLUTE PnL per trade differs across markets
- Lot size differs (NIFTY=65, BTC=1, forex lot=100k but we use 1)

---

## 2. THE NORMALIZER — `modules/data_adapters/instrument_normalizer.py`

```python
\"\"\"
modules/data_adapters/instrument_normalizer.py
\"\"\"
from dataclasses import dataclass
from typing import Optional

from .base_adapter import InstrumentInfo


@dataclass
class NormalizationProfile:
    \"\"\"
    Per-instrument scaling profile.
    Used to translate strategy concepts (ATR multiples, R-multiples) into
    market-appropriate values without changing strategy code.
    \"\"\"
    canonical_symbol: str           # strategy uses this (e.g., \"NIFTY\")
    native_symbol: str              # adapter uses this (e.g., \"BTCUSDT\")
    asset_class: str                # \"INDEX\" | \"CRYPTO\" | \"FOREX\" | \"OPTION\"
    tick_size: float                # min price increment
    lot_size: int                   # contract multiplier (NIFTY=65, BTC=1, forex=1)
    price_decimals: int             # 0 for NIFTY, 2 for BTC, 4 for EUR/USD, 2 for JPY
    notional_per_lot_quote: float   # how many quote units 1 lot represents
    typical_atr_pct: float          # typical ATR as % of price (sanity check)


# Pre-built profiles for known instruments
PROFILES = {
    # NSE Index Options
    \"NIFTY\": NormalizationProfile(
        canonical_symbol=\"NIFTY\",
        native_symbol=\"NIFTY\",
        asset_class=\"INDEX\",
        tick_size=0.05,
        lot_size=65,
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.30,  # NIFTY 5m ATR ~ 0.3% of price
    ),
    \"BANKNIFTY\": NormalizationProfile(
        canonical_symbol=\"BANKNIFTY\",
        native_symbol=\"BANKNIFTY\",
        asset_class=\"INDEX\",
        tick_size=0.05,
        lot_size=30,
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.40,
    ),
    # Crypto (via Binance)
    \"BTCUSDT\": NormalizationProfile(
        canonical_symbol=\"NIFTY\",      # NIFTY-equivalent for strategy
        native_symbol=\"BTCUSDT\",
        asset_class=\"CRYPTO\",
        tick_size=0.01,
        lot_size=1,                    # crypto is fractional, lot=1
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.50,  # crypto more volatile
    ),
    \"ETHUSDT\": NormalizationProfile(
        canonical_symbol=\"BANKNIFTY\",
        native_symbol=\"ETHUSDT\",
        asset_class=\"CRYPTO\",
        tick_size=0.01,
        lot_size=1,
        price_decimals=2,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.60,
    ),
    # Forex (via Alpha Vantage)
    \"EUR/USD\": NormalizationProfile(
        canonical_symbol=\"NIFTY\",
        native_symbol=\"EUR/USD\",
        asset_class=\"FOREX\",
        tick_size=0.0001,
        lot_size=1,                    # we use lot=1 for forex paper testing
        price_decimals=5,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.10,  # forex calmer
    ),
    \"GBP/USD\": NormalizationProfile(
        canonical_symbol=\"BANKNIFTY\",
        native_symbol=\"GBP/USD\",
        asset_class=\"FOREX\",
        tick_size=0.0001,
        lot_size=1,
        price_decimals=5,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.10,
    ),
    \"USD/JPY\": NormalizationProfile(
        canonical_symbol=\"NIFTY\",
        native_symbol=\"USD/JPY\",
        asset_class=\"FOREX\",
        tick_size=0.01,                # JPY pairs different
        lot_size=1,
        price_decimals=3,
        notional_per_lot_quote=1.0,
        typical_atr_pct=0.10,
    ),
}


def get_profile(native_symbol: str) -> Optional[NormalizationProfile]:
    \"\"\"Look up normalization profile by adapter-side symbol.\"\"\"
    return PROFILES.get(native_symbol)


def normalize_price(price: float, profile: NormalizationProfile) -> float:
    \"\"\"Round price to instrument's tick size.\"\"\"
    return round(price / profile.tick_size) * profile.tick_size


def pnl_in_quote_currency(
    entry: float, exit_price: float, lots: int, profile: NormalizationProfile,
    direction: str = \"CE\"
) -> float:
    \"\"\"Compute PnL in the instrument's quote currency (USD for crypto/forex, INR for NSE).\"\"\"
    delta = (exit_price - entry) if direction.upper() in (\"CE\", \"LONG\", \"BUY\") else (entry - exit_price)
    return delta * lots * profile.lot_size * profile.notional_per_lot_quote


def sanity_check_atr(atr: float, current_price: float, profile: NormalizationProfile) -> bool:
    \"\"\"
    Sanity check: ATR should be roughly within 0.5× to 3× the typical for this instrument.
    Detects feed errors (e.g., adapter returning prices in wrong unit).
    \"\"\"
    atr_pct = (atr / current_price) * 100
    return (profile.typical_atr_pct * 0.5) <= atr_pct <= (profile.typical_atr_pct * 3)


__all__ = [\"NormalizationProfile\", \"PROFILES\", \"get_profile\",
           \"normalize_price\", \"pnl_in_quote_currency\", \"sanity_check_atr\"]
```

---

## 3. WHAT THIS BUYS YOU

### 3.1 Strategy code never changes
Strategy continues to:
```python
df = data.get_bars(\"NIFTY\", \"5m\", 200)
atr = df[\"high\"].rolling(14).mean() - df[\"low\"].rolling(14).mean()
target = entry + 1.5 * atr.iloc[-1]
```

This works identically across crypto/forex because ATR scales with price.

### 3.2 PnL display in dashboard adapts automatically
Dashboard reads the adapter's `get_instrument_info()` → asset_class → currency symbol.
- NSE: \"₹2,847\"
- Binance: \"$284.70\"
- Forex: \"$28.47\"

### 3.3 Sanity checks catch feed errors
If Binance adapter accidentally returns prices in different units (e.g., 0.000001 instead of 105000 for BTC), the ATR sanity check fires:
```python
if not sanity_check_atr(atr, price, profile):
    raise AdapterError(f\"ATR {atr} implausible for {symbol} at price {price}\")
```

This prevents the bot from sizing positions based on broken data.

---

## 4. DASHBOARD INTEGRATION

The frontend's Dashboard / Trades tab should:
1. Call `/api/system/status` → returns active_adapter info
2. Display: `Currency: ₹` for NSE, `Currency: $` for crypto/forex
3. All P&L values use the active adapter's quote currency

Backend endpoint:
```python
@router.get(\"/api/system/active-instrument\")
def active_instrument():
    from modules.data_adapters import get_active_adapter
    from modules.data_adapters.instrument_normalizer import get_profile
    adapter = get_active_adapter()
    info = adapter.get_instrument_info(\"NIFTY\")  # canonical name
    profile = get_profile(info.native_symbol)
    return {
        \"canonical\": \"NIFTY\",
        \"native\": info.native_symbol,
        \"asset_class\": info.asset_class,
        \"quote_currency\": info.quote_currency,
        \"display_decimals\": profile.price_decimals if profile else 2,
        \"is_24x7\": info.is_24x7,
    }
```

---

## 5. STRATEGY PARAMETER ADAPTATION (optional, advanced)

Some strategy thresholds may benefit from per-asset tuning, but you said NO logic changes — so keep all thresholds at NIFTY-baseline values for now. The strategy will still produce signals on crypto/forex; whether those signals have edge is what we test.

If after testing the strategy has zero edge on crypto:
- Asset class needs different `min_confidence` thresholds (NIFTY=55, BTC might need 65 due to higher noise)
- Don't change `strategy_mapper.py` — instead override at the config layer in a future iteration

For this round: **no parameter changes. Pure data-source swap only.**

---

## 6. SELF-TEST

```python
# After Gemini writes instrument_normalizer.py:
python -c \"
from modules.data_adapters.instrument_normalizer import get_profile, PROFILES
for sym in ['NIFTY', 'BTCUSDT', 'EUR/USD', 'USD/JPY']:
    p = get_profile(sym)
    print(f'{sym:10s} | tick={p.tick_size:8.4f} | lot={p.lot_size:>6d} | class={p.asset_class:6s} | atr%={p.typical_atr_pct}')
\"
```

Expected output:
```
NIFTY      | tick=  0.0500 | lot=    65 | class=INDEX  | atr%=0.30
BTCUSDT    | tick=  0.0100 | lot=     1 | class=CRYPTO | atr%=0.50
EUR/USD    | tick=  0.0001 | lot=     1 | class=FOREX  | atr%=0.10
USD/JPY    | tick=  0.0100 | lot=     1 | class=FOREX  | atr%=0.10
```

---

**END OF NORMALIZATION SPEC. Continue to MARKET_HOURS_NORMALIZER.md.**
"
Observation: Create successful: /app/INSTRUMENT_NORMALIZATION_SPEC.md