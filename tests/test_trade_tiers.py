from modules.trade_tiers import TradeTierResolver


def test_balanced_threshold_is_lower_than_strict_threshold():
    resolver = TradeTierResolver()

    assert resolver.threshold_for_mode(65, "NORMAL") == 65
    assert resolver.threshold_for_mode(65, "BALANCED") == 56
    assert resolver.threshold_for_mode(65, "PARTICIPATION") == 50


def test_moderate_conflict_becomes_tier_b_smaller_size():
    resolver = TradeTierResolver()

    tier = resolver.classify(
        {"strategy": "STRUCTURE_BOUNCE", "confidence": 61, "raw_signal": {"setup_type": "internal_bos"}},
        mode="BALANCED",
        hierarchy_decision={"confidence_delta": -14, "warnings": []},
        manipulation_weight=0.72,
    )

    assert tier.tier == "B"
    assert tier.risk_multiplier < 0.60


def test_high_manipulation_blocks_tier_assignment():
    resolver = TradeTierResolver()

    tier = resolver.classify(
        {"strategy": "MOMENTUM_BREAKOUT", "confidence": 80, "raw_signal": {"setup_type": "external_bos"}},
        mode="PARTICIPATION",
        manipulation_weight=0.96,
    )

    assert tier.tier == "REJECT"
