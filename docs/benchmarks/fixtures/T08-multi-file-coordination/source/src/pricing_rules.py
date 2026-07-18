"""Shared pricing rules for the storefront."""
from __future__ import annotations

MEMBER_DISCOUNT_RATE = 0.15


def apply_member_discount(price: float) -> float:
    """Apply the member discount rate to a price."""
    return round(price * (1 - MEMBER_DISCOUNT_RATE), 2)
