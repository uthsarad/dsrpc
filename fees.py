"""Fee calculation utility for bank transfers.

Tier schedule (per transfer):
    - $0.00 - $2,000.00: 0% (no fee)
    - $2,000.01 - $10,000.00: 0.25%, cap $20.00
    - $10,000.01 - $20,000.00: 0.20%, cap $25.00
    - $20,000.01 - $50,000.00: 0.125%, cap $40.00
    - $50,000.01 - $100,000.00: 0.08%, cap $50.00
    - $100,000.01+: 0.05%, cap $100.00
"""

import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence


@dataclass(frozen=True)
class FeeTier:
    upper_bound: Optional[Decimal]
    rate: Decimal
    cap: Optional[Decimal]


TIERS: Sequence[FeeTier] = (
    FeeTier(Decimal("2000.00"), Decimal("0"), None),
    FeeTier(Decimal("10000.00"), Decimal("0.0025"), Decimal("20.00")),
    FeeTier(Decimal("20000.00"), Decimal("0.0020"), Decimal("25.00")),
    FeeTier(Decimal("50000.00"), Decimal("0.00125"), Decimal("40.00")),
    FeeTier(Decimal("100000.00"), Decimal("0.0008"), Decimal("50.00")),
    FeeTier(None, Decimal("0.0005"), Decimal("100.00")),
)


def compute_fee(amount: float) -> float:
    """Calculate the transfer fee for a given amount."""
    _validate_amount(amount)

    amt = Decimal(str(amount))
    fee = Decimal("0")

    for tier in TIERS:
        if tier.upper_bound is None or amt <= tier.upper_bound:
            fee = amt * tier.rate
            if tier.cap is not None and fee > tier.cap:
                fee = tier.cap
            break

    return float(fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _validate_amount(amount: float) -> None:
    if not math.isfinite(amount):
        raise ValueError("Amount cannot be NaN or infinite")
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
