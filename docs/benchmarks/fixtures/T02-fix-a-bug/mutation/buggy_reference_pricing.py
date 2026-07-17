"""Bulk-order pricing for a small inventory system."""
from __future__ import annotations


def apply_tier_discount(quantity: int, unit_price: float) -> float:
    """Bulk discount: 10% off for 10-49 units, 20% off for 50+ units,
    no discount below 10 units."""
    total = quantity * unit_price
    if 10 <= quantity < 50:
        return total * 0.9
    elif quantity > 50:
        return total * 0.8
    return total
