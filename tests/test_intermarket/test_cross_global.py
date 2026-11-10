import pytest
from modules.intermarket.cross_asset import CrossAssetContextEngine
from modules.intermarket.global_risk import GlobalRiskContext
from modules.intermarket.schemas import CrossAssetSnapshot

def test_cross_asset_it_rupee():
    engine = CrossAssetContextEngine()
    # Weak rupee (usdinr up) is GOOD for IT exporters
    snapshot = CrossAssetSnapshot(
        usdinr={'session_return': 0.005}, # +0.5%
        crude={}, gold={}, india_vix={}, sgx_nifty={}
    )
    
    # INFY is USDINR_SENSITIVE
    verdict = engine.evaluate("INFY", "LONG", snapshot)
    assert verdict.score_delta == 0.5
    assert "USDINR" in verdict.relevant_assets

def test_cross_asset_indigo_crude():
    engine = CrossAssetContextEngine()
    # High crude is BAD for INDIGO (Aviation)
    snapshot = CrossAssetSnapshot(
        crude={'session_return': 0.01}, # +1.0%
        usdinr={}, gold={}, india_vix={}, sgx_nifty={}
    )
    
    verdict = engine.evaluate("INDIGO", "LONG", snapshot)
    assert verdict.score_delta == -0.6

def test_global_risk_sentiment():
    engine = GlobalRiskContext()
    # 5 indices up 0.4%
    snapshot = {f"IDX_{i}": 0.004 for i in range(5)}
    verdict = engine.evaluate(snapshot)
    assert verdict.sentiment == "RISK_ON_BROAD"
    assert verdict.score_delta == 0.5
