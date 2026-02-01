import pytest
from decimal import Decimal, ROUND_HALF_UP
from fees import compute_fee
import math


def to_decimal(value: float) -> Decimal:
    """Helper to convert float result to Decimal for precise comparison."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TestFeeTiers:
    """Test fee calculation across all tiers and boundaries."""
    
    # Tier 1: Free tier ($0.00 - $2,000.00)
    def test_free_tier_minimum(self):
        result = compute_fee(0.01)
        assert to_decimal(result) == Decimal("0.00")
    
    def test_free_tier_maximum(self):
        result = compute_fee(2000.00)
        assert to_decimal(result) == Decimal("0.00")
    
    # Tier 2: Entry tier ($2,000.01 - $10,000.00, 0.25%, cap $20)
    def test_entry_tier_boundary_lower(self):
        result = compute_fee(2000.01)
        # 2000.01 * 0.0025 = 5.0000 -> $5.00
        assert to_decimal(result) == Decimal("5.00")
    
    def test_entry_tier_mid(self):
        result = compute_fee(5000.00)
        # 5000.00 * 0.0025 = 12.50 (under cap)
        assert to_decimal(result) == Decimal("12.50")
    
    def test_entry_tier_cap_triggered(self):
        result = compute_fee(10000.00)
        # 10000.00 * 0.0025 = 25.00, capped at $20.00
        assert to_decimal(result) == Decimal("20.00")
    
    # Tier 3: Mid tier ($10,000.01 - $20,000.00, 0.20%, cap $25)
    def test_mid_tier_boundary_lower(self):
        result = compute_fee(10000.01)
        # 10000.01 * 0.0020 = 20.0000 (under cap)
        assert to_decimal(result) == Decimal("20.00")
    
    def test_mid_tier_cap_triggered(self):
        result = compute_fee(20000.00)
        # 20000.00 * 0.0020 = 40.00, capped at $25.00
        assert to_decimal(result) == Decimal("25.00")
    
    # Tier 4: Upper-mid tier ($20,000.01 - $50,000.00, 0.125%, cap $40)
    def test_upper_mid_tier_boundary_lower(self):
        result = compute_fee(20000.01)
        # 20000.01 * 0.00125 = 25.0000 (under cap)
        assert to_decimal(result) == Decimal("25.00")
    
    def test_upper_mid_tier_cap_triggered(self):
        result = compute_fee(50000.00)
        # 50000.00 * 0.00125 = 62.50, capped at $40.00
        assert to_decimal(result) == Decimal("40.00")
    
    # Tier 5: High tier ($50,000.01 - $100,000.00, 0.08%, cap $50)
    def test_high_tier_boundary_lower(self):
        result = compute_fee(50000.01)
        # 50000.01 * 0.0008 = 40.0000 (under cap)
        assert to_decimal(result) == Decimal("40.00")
    
    def test_high_tier_cap_triggered(self):
        result = compute_fee(100000.00)
        # 100000.00 * 0.0008 = 80.00, capped at $50.00
        assert to_decimal(result) == Decimal("50.00")
    
    # Tier 6: Top tier ($100,000.01+, 0.05%, cap $100)
    def test_top_tier_boundary_lower(self):
        result = compute_fee(100000.01)
        # 100000.01 * 0.0005 = 50.0000 (under cap)
        assert to_decimal(result) == Decimal("50.00")
    
    def test_top_tier_cap_triggered(self):
        result = compute_fee(500000.00)
        # 500000.00 * 0.0005 = 250.00, capped at $100.00
        assert to_decimal(result) == Decimal("100.00")
    
    def test_top_tier_extremely_large(self):
        result = compute_fee(1_000_000_000.00)
        # 1B * 0.0005 = 500,000, capped at $100.00
        assert to_decimal(result) == Decimal("100.00")


class TestInvalidInputs:
    """Test error handling for invalid inputs."""
    
    def test_zero_amount(self):
        with pytest.raises(ValueError, match="must be greater than 0"):
            compute_fee(0)
    
    def test_negative_amount(self):
        with pytest.raises(ValueError, match="must be greater than 0"):
            compute_fee(-100.00)
    
    def test_nan_amount(self):
        with pytest.raises(ValueError, match="cannot be NaN"):
            compute_fee(math.nan)
    
    def test_infinite_amount(self):
        with pytest.raises(ValueError, match="cannot be NaN or infinite"):
            compute_fee(math.inf)


class TestRounding:
    """Test proper rounding behavior."""
    
    def test_rounding_half_up(self):
        # Test that ROUND_HALF_UP is applied correctly
        # 2000.01 * 0.0025 = 5.000025, should round to 5.00
        result = compute_fee(2000.01)
        assert to_decimal(result) == Decimal("5.00")
    
    def test_rounding_precision(self):
        # Amount that produces fee requiring rounding
        # 3333.33 * 0.0025 = 8.333325, should round to 8.33
        result = compute_fee(3333.33)
        assert to_decimal(result) == Decimal("8.33")
