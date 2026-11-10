import pytest
from modules.intermarket.aggregator import IntermarketAggregator
from modules.intermarket.schemas import IndexAlignmentVerdict

def test_aggregator_simple_sum():
    agg = IntermarketAggregator()
    
    # Mock some sub-verdicts
    v1 = IndexAlignmentVerdict(
        nifty_state="BULL", banknifty_state=None, alignment="ALIGNED", 
        score_delta=0.5, veto=False, override_applied=None, reasoning="test"
    )
    
    sub_verdicts = {'index': v1}
    
    # TRENDING_LOW_VOL has weight 1.0
    verdict = agg.aggregate(sub_verdicts, "TRENDING_LOW_VOL", "TREND_CONTINUATION", "OPENING_BURST")
    
    # TREND_CONTINUATION has weight 1.2
    assert verdict.raw_combined_delta == 0.5
    assert verdict.final_delta == pytest.approx(0.6)
    assert verdict.allow == True

def test_aggregator_veto():
    agg = IntermarketAggregator()
    
    v1 = IndexAlignmentVerdict(
        nifty_state="STRONG_BEAR", banknifty_state=None, alignment="CONTRA_STRONG", 
        score_delta=-1.5, veto=True, override_applied=None, reasoning="veto test"
    )
    
    sub_verdicts = {'index': v1}
    verdict = agg.aggregate(sub_verdicts, "TRENDING_LOW_VOL", "TREND_CONTINUATION", "OPENING_BURST")
    
    assert verdict.allow == False
    assert len(verdict.veto_reasons) > 0
