import pandas as pd
import yaml
from typing import Dict, Any, List, Optional
from modules.intermarket.schemas import CrossAssetVerdict, CrossAssetSnapshot
from modules.intermarket.universe_mapper import SymbolUniverseMapper

class CrossAssetContextEngine:
    def __init__(self, config_path: str = "config/intermarket.yaml", universe_mapper: Optional[SymbolUniverseMapper] = None):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['cross_asset']
        self.mapper = universe_mapper or SymbolUniverseMapper()

    def evaluate(self, symbol: str, direction: str, cross_assets: CrossAssetSnapshot) -> CrossAssetVerdict:
        tags = self.mapper.get_cross_asset_tags(symbol)
        score_delta = 0.0
        relevant_assets = []
        asset_states = {}
        c = self.config
        
        # 1. USDINR Sensitive (IT, Pharma)
        if "USDINR_SENSITIVE" in tags:
            relevant_assets.append("USDINR")
            usdinr_ret = cross_assets.usdinr.get('session_return', 0)
            asset_states['USDINR_ret'] = usdinr_ret
            if abs(usdinr_ret) >= c['usdinr_session_threshold_pct'] / 100:
                if direction == "LONG":
                    score_delta += c['score_deltas']['usdinr_aligned'] if usdinr_ret > 0 else -c['score_deltas']['usdinr_aligned']
                else:
                    score_delta += c['score_deltas']['usdinr_aligned'] if usdinr_ret < 0 else -c['score_deltas']['usdinr_aligned']

        # 2. Crude Sensitive
        if "CRUDE_SENSITIVE" in tags:
            relevant_assets.append("CRUDE")
            crude_ret = cross_assets.crude.get('session_return', 0)
            asset_states['CRUDE_ret'] = crude_ret
            industry = self.mapper.get_industry(symbol)
            
            if abs(crude_ret) >= c['crude_session_threshold_pct'] / 100:
                if "Aviation" in industry:
                    if crude_ret > 0: score_delta += c['score_deltas']['crude_aviation_long_on_up'] if direction == "LONG" else -c['score_deltas']['crude_aviation_long_on_up']
                elif "Oil & Gas" in industry:
                    if crude_ret > 0: score_delta += c['score_deltas']['crude_omc_long_on_up'] if direction == "LONG" else -c['score_deltas']['crude_omc_long_on_up']
                elif "Paints" in industry:
                    if crude_ret > 0: score_delta += c['score_deltas']['crude_paint_long_on_up'] if direction == "LONG" else -c['score_deltas']['crude_paint_long_on_up']

        # 3. VIX (Universal Impact)
        vix_ret = cross_assets.india_vix.get('session_return', 0)
        asset_states['VIX_ret'] = vix_ret
        if vix_ret >= c['vix_session_threshold_pct'] / 100:
            score_delta += c['score_deltas']['vix_up_favours_short'] if direction == "SHORT" else -c['score_deltas']['vix_up_favours_short']

        reasoning = f"Relevant: {relevant_assets} | Score Delta: {score_delta:.2f}"
        
        return CrossAssetVerdict(
            relevant_assets=relevant_assets,
            asset_states=asset_states,
            score_delta=score_delta,
            reasoning=reasoning
        )
