import pytest
import os
from modules.intermarket.universe_mapper import SymbolUniverseMapper

def test_mapper_loads_correctly():
    mapper = SymbolUniverseMapper("config/universe.yaml")
    assert "RELIANCE" in mapper.get_all_symbols()
    assert mapper.get_sector("RELIANCE") == "NIFTY_ENERGY"
    assert "CRUDE_SENSITIVE" in mapper.get_cross_asset_tags("RELIANCE")

def test_mapper_indices():
    mapper = SymbolUniverseMapper("config/universe.yaml")
    indices = mapper.get_indices("HDFCBANK")
    assert "NIFTY_50" in indices
    assert "NIFTY_FINSERV" in indices

def test_mapper_beta_fallback():
    mapper = SymbolUniverseMapper("config/universe.yaml")
    # RELIANCE base_beta is 1.15, refresh adds +/- 0.02
    beta = mapper.get_beta("RELIANCE")
    assert beta == pytest.approx(1.15, abs=0.03)

def test_peers_in_sector():
    mapper = SymbolUniverseMapper("config/universe.yaml")
    peers = mapper.peers_in_sector("HDFCBANK")
    # ICICIBANK and SBIN are also in NIFTY_BANK in our config
    assert "ICICIBANK" in peers
    assert "SBIN" in peers
    assert "HDFCBANK" not in peers
