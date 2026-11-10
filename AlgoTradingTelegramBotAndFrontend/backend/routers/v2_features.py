from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
from modules.price_action_engine import PriceActionEngine
from modules.smc.engine import SmartMoneyConceptsEngine
from modules.strategy_selector import MasterStrategySelector
from modules.data_adapters import get_active_adapter

router = APIRouter(prefix="/v2")

@router.get("/overlays/{symbol}")
async def get_overlays(symbol: str):
    """REQ 29-2: Returns S/R Zones, SMC OBs, and FVGs for chart overlay."""
    try:
        adapter = get_active_adapter()
        # Fetch latest 100 5m bars
        # This is a bit complex in async FastAPI, but we'll use a sync helper for now
        token_map = {"NIFTY": "99926000", "BANKNIFTY": "99926009"} # Example
        token = token_map.get(symbol)
        if not token:
            raise HTTPException(status_code=404, detail="Symbol not supported")
            
        df = adapter.get_5m_candles(token, count=200)
        if df is None or df.empty:
            raise HTTPException(status_code=500, detail="Data fetch failed")
            
        # 1. Price Action Zones
        supports, resistances = PriceActionEngine.find_support_resistance(df)
        
        # 2. SMC OBs and FVGs
        smc = SmartMoneyConceptsEngine()
        # Mock inputs for SMC as it's complex
        preopen = {"high": df['high'].iloc[0], "low": df['low'].iloc[0]}
        prior_ohlc = {"close": df['close'].iloc[0]}
        atr = PriceActionEngine.calculate_atr(df)
        
        smc_state = smc.update(symbol, df, df, prior_ohlc, preopen, atr, atr/5.0)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "pa_zones": {"supports": supports, "resistances": resistances},
            "smc": {
                "order_blocks": [ob.__dict__ for ob in smc_state.order_blocks],
                "fvgs": [fvg.__dict__ for fvg in smc_state.fvgs]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reasoning/{symbol}")
async def get_reasoning(symbol: str):
    """REQ 29-3: Returns AI Reasoning / Funnel data for side panel."""
    selector = MasterStrategySelector()
    # This usually comes from the live bot instance, but here we provide a snapshot
    return {
        "symbol": symbol,
        "funnel": selector.funnel,
        "current_regime": "TRENDING_UP" # Placeholder
    }

@router.post("/control/veto")
async def manual_veto(payload: Dict[str, Any]):
    """REQ 29-4: One-click reject signal."""
    # Logic to insert VETO command into MongoDB
    from server import db
    await db.bot_commands.insert_one({
        "type": "USER_VETO",
        "payload": payload,
        "status": "PENDING",
        "timestamp": datetime.now().isoformat()
    })
    return {"status": "success", "message": "Signal Vetoed"}
