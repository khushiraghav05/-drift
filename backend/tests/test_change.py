import pytest
from models import Snapshot, Freshness
from services.change_engine import compute_price_signal, assess_change

def test_compute_price_signal():
    base = Snapshot(symbol="TEST", price=100.0)
    curr = Snapshot(symbol="TEST", price=106.0)
    
    # 6% move is > 5% max threshold, so raw score should be 100, weighted 30
    signal = compute_price_signal(base, curr)
    assert signal.available is True
    assert signal.signal_score == 100.0
    assert signal.weighted_score == 30.0

def test_assess_change_missing_data():
    base = Snapshot(symbol="TEST", price=100.0)
    # Missing volume, high/low, etc.
    curr = Snapshot(symbol="TEST", price=100.0)
    
    assessment = assess_change(base, curr, Freshness.LIVE, "Test Stock")
    assert assessment.score == 0.0
    assert assessment.level.value == "normal"
