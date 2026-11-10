import os
import json
import logging
import pandas as pd
from datetime import datetime
from colorama import init, Fore, Style

from modules.broker_layer import AngelOneBroker
from modules.smc.engine import SmartMoneyConceptsEngine
from modules.context_detector import ContextDetector
from modules.smc.schemas import SMCState

init(autoreset=True)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("SMC_Scanner")

def scan_instruments():
    # 1. Initialize Components
    broker = AngelOneBroker()
    if not broker.login():
        logger.error(Fore.RED + "Failed to login to Angel One.")
        return

    smc_engine = SmartMoneyConceptsEngine()
    context_detector = ContextDetector()

    # Define our universe
    symbols = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
        "BAJAJAUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL",
        "BRITANNIA", "CIPLA", "HDFCBANK", "ICICIBANK", "RELIANCE", "SBIN"
    ]

    # Load tokens
    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    print(Fore.CYAN + f"\n{'='*80}")
    print(Fore.CYAN + f" INSTITUTION-GRADE SMC SCANNER ".center(80))
    print(Fore.CYAN + f" {'='*80}\n")

    for symbol in symbols:
        token = token_map.get(f"{symbol}-EQ")
        if not token:
            continue

        print(Fore.WHITE + f"Scanning {symbol}...")
        
        # Fetch 5 days of 1-minute data to build both 1m and 5m
        df_1m = broker.get_historical_data(f"{symbol}-EQ", token, interval="ONE_MINUTE", days=5)
        if df_1m is None or df_1m.empty:
            print(Fore.RED + f"  [REJECTED] {symbol}: Failed to fetch data.")
            continue
            
        df_1m.index = df_1m.index.tz_localize(None)
        df_1m.columns = [c.lower() for c in df_1m.columns]
        df_5m = df_1m.resample('5min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        
        # 15m for HTF bias
        df_15m = df_1m.resample('15min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()

        if len(df_5m) < 50:
            print(Fore.RED + f"  [REJECTED] {symbol}: Insufficient data.")
            continue

        # Calculate Context & Volatility
        vix_proxy = 15.0  # Placeholder, can fetch real VIX if needed
        ctx = context_detector.detect(df_5m, vix_proxy)
        
        # Calculate ATR
        high = df_5m['high']
        low = df_5m['low']
        close_prev = df_5m['close'].shift(1)
        tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
        atr_5m = tr.rolling(14).mean().iloc[-1]
        
        # Calculate HTF Bias (Simple EMA 20 slope on 15m)
        ema_15m = df_15m['close'].ewm(span=20, adjust=False).mean()
        htf_bias = "BULLISH" if ema_15m.iloc[-1] > ema_15m.iloc[-2] else "BEARISH"

        # Prior Session and Preopen
        latest_date = df_5m.index[-1].date()
        prior_session = df_5m[df_5m.index.date < latest_date]
        if len(prior_session) > 0:
            prior_session_ohlc = {
                'open':  prior_session['open'].iloc[0],
                'high':  prior_session['high'].max(),
                'low':   prior_session['low'].min(),
                'close': prior_session['close'].iloc[-1],
            }
        else:
            prior_session_ohlc = {'open': df_5m['open'].iloc[0], 'high': df_5m['high'].max(), 'low': df_5m['low'].min(), 'close': df_5m['close'].iloc[-1]}

        today_session = df_5m[df_5m.index.date == latest_date]
        if len(today_session) >= 3:
            preopen_range = {'high': today_session['high'].iloc[:3].max(), 'low':  today_session['low'].iloc[:3].min()}
        else:
            preopen_range = {'high': df_5m['high'].iloc[-3:].max(), 'low':  df_5m['low'].iloc[-3:].min()}

        # Run SMC Engine
        smc_state = smc_engine.update(
            symbol=symbol,
            ohlcv_5m=df_5m,
            ohlcv_1m=df_1m,
            prior_session_ohlc=prior_session_ohlc,
            preopen_range=preopen_range,
            atr_5m=atr_5m,
            atr_1m=atr_5m/5.0
        )

        current_price = df_5m['close'].iloc[-1]

        # --- FILTERS & REJECTION LOGIC ---
        rejections = []
        
        # 1. Regime Filter
        if ctx.regime in ["CHOPPY", "VOLATILE_CHOP"]:
            rejections.append(f"Regime Check Failed: {ctx.regime} (Requires Trend or Mean_Reverting_High_Vol)")

        # 2. Volatility Check
        atr_pct = (atr_5m / current_price) * 100
        if atr_pct < 0.1:
            rejections.append(f"Volatility Check Failed: ATR% ({atr_pct:.2f}%) < 0.1% minimum")

        # 3. Structure & HTF Alignment
        if smc_state.structure.current_state == "UPTREND" and htf_bias != "BULLISH":
            rejections.append(f"HTF Alignment Failed: 5m UPTREND but 15m is {htf_bias}")
        elif smc_state.structure.current_state == "DOWNTREND" and htf_bias != "BEARISH":
            rejections.append(f"HTF Alignment Failed: 5m DOWNTREND but 15m is {htf_bias}")

        # 4. Liquidity Sweep Confirmation
        active_sweeps = [s for s in smc_state.active_sweeps if s.status == "ACTIVE"]
        if not active_sweeps:
            rejections.append("Liquidity Check Failed: No recent active liquidity sweeps (PDH/PDL/SH/SL).")

        # 5. BOS/CHOCH Alignment
        recent_choch = smc_state.structure.last_CHoCH
        recent_bos = smc_state.structure.last_BOS
        has_struct_break = False
        if recent_choch and (len(df_5m) - recent_choch.get('bar_idx', 0)) < 15:
            has_struct_break = True
        if recent_bos and (len(df_5m) - recent_bos.get('bar_idx', 0)) < 15:
            has_struct_break = True
            
        if not has_struct_break:
            rejections.append("Structure Check Failed: No recent BOS or CHoCH within 15 bars.")

        # 6. FVG / Order Block Reaction
        active_obs = [ob for ob in smc_state.order_blocks_5m if ob.status == "ACTIVE"]
        near_ob = False
        for ob in active_obs:
            if abs(current_price - ob.ob_high) < atr_5m or abs(current_price - ob.ob_low) < atr_5m:
                near_ob = True
                break
        if not near_ob:
            rejections.append("Confirmation Check Failed: Price not reacting at a valid Order Block.")

        # --- EVALUATION ---
        if rejections:
            for r in rejections:
                print(Fore.YELLOW + f"    - {r}")
            continue

        # If it passed filters, calculate RR and Score
        direction = "LONG" if smc_state.structure.current_state == "UPTREND" else "SHORT"
        
        # Target = Next Liquidity Pool or structure extreme
        if direction == "LONG":
            target = df_5m['high'].iloc[-20:].max()
            sl = current_price - (atr_5m * 1.5)
        else:
            target = df_5m['low'].iloc[-20:].min()
            sl = current_price + (atr_5m * 1.5)

        risk = abs(current_price - sl)
        reward = abs(target - current_price)
        rr = reward / risk if risk > 0 else 0

        if rr < 2.0:
            print(Fore.YELLOW + f"    - R:R Check Failed: {rr:.2f} < 2.0 minimum required.")
            continue

        # Score the setup
        score_res = smc_engine.score_signal(
            candidate_entry=current_price,
            candidate_direction=direction,
            smc_state=smc_state,
            level_set=None,
            regime=ctx.regime,
            atr_5m=atr_5m
        )

        threshold = 2.0 # ELITE or MONEY tier
        if score_res.raw_score >= threshold:
            print(Fore.GREEN + f"  [APPROVED] {symbol} | Dir: {direction} | Score: {score_res.raw_score} ({score_res.tier_label})")
            print(Fore.GREEN + f"    -> Entry: {current_price:.2f} | SL: {sl:.2f} | TP: {target:.2f} | R:R: {rr:.2f}")
            print(Fore.GREEN + f"    -> Convictions: {score_res.reasoning}")
        else:
            print(Fore.YELLOW + f"    - Score Check Failed: {score_res.raw_score} < {threshold} threshold. Tier: {score_res.tier_label}")

if __name__ == "__main__":
    scan_instruments()
