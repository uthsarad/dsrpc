import math
from decimal import Decimal, ROUND_HALF_UP

import pytest

from fees import compute_fee


def to_decimal(value: float) -> Decimal:
    """Helper to convert float result to Decimal for precise comparison."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0.01, Decimal("0.00")),
        (2000.00, Decimal("0.00")),
        (2000.01, Decimal("5.00")),
        (5000.00, Decimal("12.50")),
        (10000.00, Decimal("20.00")),
        (10000.01, Decimal("20.00")),
        (20000.00, Decimal("25.00")),
        (20000.01, Decimal("25.00")),
        (50000.00, Decimal("40.00")),
        (50000.01, Decimal("40.00")),
        (100000.00, Decimal("50.00")),
        (100000.01, Decimal("50.00")),
        (500000.00, Decimal("100.00")),
        (1_000_000_000.00, Decimal("100.00")),
    ],
    ids=[
        "free-tier-minimum",
        "free-tier-maximum",
        "entry-tier-lower-bound",
        "entry-tier-mid",
        "entry-tier-cap",
        "mid-tier-lower-bound",
        "mid-tier-cap",
        "upper-mid-tier-lower-bound",
        "upper-mid-tier-cap",
        "high-tier-lower-bound",
        "high-tier-cap",
        "top-tier-lower-bound",
        "top-tier-cap",
        "top-tier-large-amount",
    ],
)
def test_fee_tiers(amount, expected):
    assert to_decimal(compute_fee(amount)) == expected


@pytest.mark.parametrize(
    ("amount", "message"),
    [
        (0, "must be greater than 0"),
        (-100.00, "must be greater than 0"),
        (math.nan, "cannot be NaN"),
        (math.inf, "cannot be NaN or infinite"),
    ],
)
def test_invalid_inputs(amount, message):
    with pytest.raises(ValueError, match=message):
        compute_fee(amount)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (2000.01, Decimal("5.00")),
        (3333.33, Decimal("8.33")),
    ],
)
def test_rounding(amount, expected):
    assert to_decimal(compute_fee(amount)) == expected
