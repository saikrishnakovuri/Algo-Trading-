import requests
import pandas as pd
import math
from typing import Optional, Tuple, Dict


def _safe_float(x, default: float = 0.0) -> float:
    """Lightweight safe float conversion handling pandas/numpy scalars/series."""
    try:
        import numpy as _np
        # None
        if x is None:
            return float(default)

        # pandas Series / Index
        if isinstance(x, (pd.Series, pd.Index)):
            try:
                return float(x.iloc[-1])
            except Exception:
                try:
                    arr = _np.asarray(x)
                    if arr.size == 0:
                        return float(default)
                    return float(arr.ravel()[-1])
                except Exception:
                    return float(default)

        # numpy array
        if isinstance(x, (_np.ndarray,)):
            try:
                return float(x.item())
            except Exception:
                try:
                    arr = _np.asarray(x)
                    return float(arr.ravel()[-1])
                except Exception:
                    return float(default)

        # plain python scalar
        return float(x)
    except Exception:
        try:
            return float(x)
        except Exception:
            return float(default)

def fetch_option_chain(underlying_price: Optional[float] = None, use_nse_api: bool = False) -> pd.DataFrame:
    """
    Attempt to fetch real option chain from NSE. If unavailable or blocked,
    return a deterministic simulated DataFrame centered on `underlying_price`.

    Columns: strike, CE_OI, PE_OI, CE_change, PE_change, CE_volume, PE_volume
    """
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.nseindia.com/"
    }

    if use_nse_api:
        try:
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=headers, timeout=5)
            resp = session.get(url, headers=headers, timeout=5)
            data = resp.json()
            records = data.get('records', {}).get('data', [])

            rows = []
            for item in records:
                strike = item.get('strikePrice')
                ce = item.get('CE', {}) or {}
                pe = item.get('PE', {}) or {}

                rows.append({
                    'strike': _safe_float(strike),
                    'CE_OI': int(ce.get('openInterest', 0)),
                    'PE_OI': int(pe.get('openInterest', 0)),
                    'CE_change': int(ce.get('changeinOpenInterest', 0) or 0),
                    'PE_change': int(pe.get('changeinOpenInterest', 0) or 0),
                    'CE_volume': int(ce.get('totalTradedVolume', 0) or 0),
                    'PE_volume': int(pe.get('totalTradedVolume', 0) or 0),
                })

            df = pd.DataFrame(rows)
            if not df.empty:
                return df.sort_values('strike').reset_index(drop=True)
        except Exception:
            # fall through to deterministic simulation
            pass

    # Deterministic simulation fallback
    try:
        if underlying_price is None:
            # lazy import to avoid cycles
            import yfinance as yf
            data = yf.download("^NSEI", period="1d", interval="15m")
            underlying_price = _safe_float(data['close'].iloc[-1])
    except Exception:
        # final fallback price
        underlying_price = underlying_price or 22400.0

    step = 50
    half_width = 1000
    center = int(round(underlying_price / step) * step)
    strikes = list(range(center - half_width, center + half_width + 1, step))

    rows = []
    for strike in strikes:
        distance = abs(strike - underlying_price)
        # base OI decays with distance; deterministic and non-random
        base = max(50, int(5000 - distance * 3))

        # bias CE/PE around the underlying price to create realistic structure
        ce_oi = int(base * (1.15 if strike >= underlying_price else 0.85))
        pe_oi = int(base * (1.15 if strike <= underlying_price else 0.85))

        # create deterministic OI changes (positive means buildup)
        ce_change = int((underlying_price - strike) / max(1, step))  # negative above
        pe_change = -ce_change

        rows.append({
            'strike': _safe_float(strike),
            'CE_OI': max(0, ce_oi),
            'PE_OI': max(0, pe_oi),
            'CE_change': int(ce_change),
            'PE_change': int(pe_change),
            'CE_volume': max(0, int(ce_oi / 10)),
            'PE_volume': max(0, int(pe_oi / 10)),
        })

    df = pd.DataFrame(rows)
    return df.sort_values('strike').reset_index(drop=True)


def find_strong_levels(df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
    if df is None or df.empty:
        return None, None

    try:
        resistance = _safe_float(df.loc[df['CE_OI'].idxmax()]['strike'])
    except Exception:
        resistance = None

    try:
        support = _safe_float(df.loc[df['PE_OI'].idxmax()]['strike'])
    except Exception:
        support = None

    return support, resistance


def calculate_pcr(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    total_pe = int(df['PE_OI'].sum())
    total_ce = int(df['CE_OI'].sum())
    if total_ce == 0:
        return float('inf') if total_pe > 0 else 0.0
    return float(total_pe) / float(total_ce)


def analyze_oi_change(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "NEUTRAL"
    ce_change = int(df['CE_change'].sum())
    pe_change = int(df['PE_change'].sum())

    if pe_change > ce_change:
        return "BULLISH_BUILDUP"
    elif ce_change > pe_change:
        return "BEARISH_BUILDUP"
    else:
        return "NEUTRAL"


def option_chain_signal(df: pd.DataFrame) -> Dict[str, object]:
    support, resistance = find_strong_levels(df)
    pcr = calculate_pcr(df)
    oi_trend = analyze_oi_change(df)

    if pcr > 1 and oi_trend == "BULLISH_BUILDUP":
        bias = "BULLISH"
    elif pcr < 1 and oi_trend == "BEARISH_BUILDUP":
        bias = "BEARISH"
    else:
        bias = "SIDEWAYS"

    return {
        'support': support,
        'resistance': resistance,
        'pcr': round(pcr, 2) if isinstance(pcr, float) else pcr,
        'oi_trend': oi_trend,
        'bias': bias,
    }
