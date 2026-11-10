from modules.narrative_hierarchy import NarrativeHierarchyResolver


def test_1m_bullish_bos_15m_bearish_ebos_vetoes_long():
    resolver = NarrativeHierarchyResolver()

    decision = resolver.resolve(
        {
            "1m": {"bias": "BULL", "confidence": 0.68, "state": "internal_bos"},
            "15m": {"bias": "BEAR", "confidence": 0.92, "state": "external_bos"},
        },
        trade_direction="CE",
        base_confidence=72,
    )

    assert decision["dominant_bias"] == "BEAR"
    assert decision["trade_allowed"] is False
    assert decision["adjusted_confidence"] < 72
    assert "15m" in decision["reason"]


def test_bullish_alignment_boosts_confidence():
    resolver = NarrativeHierarchyResolver()

    decision = resolver.resolve(
        {
            "1m": {"bias": "BULL", "confidence": 0.68, "state": "internal_bos"},
            "5m": {"bias": "BULL", "confidence": 0.81, "state": "retest_confirmation"},
            "15m": {"bias": "BULL", "confidence": 0.92, "state": "external_bos"},
        },
        trade_direction="CE",
        base_confidence=70,
    )

    assert decision["dominant_bias"] == "BULL"
    assert decision["trade_allowed"] is True
    assert decision["adjusted_confidence"] > 70
    assert decision["confidence_delta"] > 0


def test_htf_bearish_distribution_ltf_bullish_sweep_warns_trap():
    resolver = NarrativeHierarchyResolver()

    decision = resolver.resolve(
        {
            "1m": {"bias": "BULL", "confidence": 0.70, "state": "liquidity_sweep"},
            "15m": {"bias": "BEAR", "confidence": 0.88, "state": "distribution"},
            "memory": {"bias": "BEAR", "confidence": 0.80, "state": "double_sweep"},
        },
        trade_direction="CE",
        base_confidence=76,
    )

    assert decision["dominant_bias"] == "BEAR"
    assert decision["trade_allowed"] is False
    assert decision["adjusted_confidence"] < 76
    assert decision["warnings"]
