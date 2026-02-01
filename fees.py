from decimal import Decimal, ROUND_HALF_UP
import math


def compute_fee(amount: float) -> float:
    """
    Calculate transfer fee based on tiered fee structure.
    
    Fee tiers (per transfer):
    - $0.00 - $2,000.00: 0% (no fee)
    - $2,000.01 - $10,000.00: 0.25%, cap $20.00
    - $10,000.01 - $20,000.00: 0.20%, cap $25.00
    - $20,000.01 - $50,000.00: 0.125%, cap $40.00
    - $50,000.01 - $100,000.00: 0.08%, cap $50.00
    - $100,000.01+: 0.05%, cap $100.00
    
    Args:
        amount: Transfer amount (must be > 0)
        
    Returns:
        Fee rounded to 2 decimal places
        
    Raises:
        ValueError: If amount <= 0, NaN, or infinite
    """
    # Validate input
    if math.isnan(amount) or math.isinf(amount):
        raise ValueError("Amount cannot be NaN or infinite")
    
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
    
    # Convert to Decimal for precise currency calculations
    amt = Decimal(str(amount))
    
    # Define fee tiers: (upper_bound, percentage, cap)
    # None for upper_bound means no upper limit
    tiers = [
        (Decimal("2000.00"), Decimal("0"), None),
        (Decimal("10000.00"), Decimal("0.0025"), Decimal("20.00")),
        (Decimal("20000.00"), Decimal("0.0020"), Decimal("25.00")),
        (Decimal("50000.00"), Decimal("0.00125"), Decimal("40.00")),
        (Decimal("100000.00"), Decimal("0.0008"), Decimal("50.00")),
        (None, Decimal("0.0005"), Decimal("100.00")),
    ]
    
    # Determine tier and calculate fee
    fee = Decimal("0")
    
    for upper_bound, percentage, cap in tiers:
        if upper_bound is None or amt <= upper_bound:
            # Calculate percentage-based fee
            fee = amt * percentage
            
            # Apply cap if present
            if cap is not None and fee > cap:
                fee = cap
            
            break
    
    # Round to 2 decimal places using financial rounding
    fee = fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Convert back to float for return
    return float(fee)
