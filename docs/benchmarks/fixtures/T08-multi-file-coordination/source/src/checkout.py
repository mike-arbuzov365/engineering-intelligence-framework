"""Checkout total calculation for the storefront."""
from __future__ import annotations

from pricing_rules import apply_member_discount


def compute_order_total(item_prices: list[float], is_member: bool) -> float:
    """Total of item_prices, with the member discount applied if is_member."""
    subtotal = sum(item_prices)
    if is_member:
        return apply_member_discount(subtotal)
    return round(subtotal, 2)


def compute_single_item_price(price: float, is_member: bool) -> float:
    """Price for a single item, with the member discount applied if
    is_member - same rate compute_order_total uses."""
    if is_member:
        return round(price * (1 - 0.10), 2)
    return round(price, 2)
