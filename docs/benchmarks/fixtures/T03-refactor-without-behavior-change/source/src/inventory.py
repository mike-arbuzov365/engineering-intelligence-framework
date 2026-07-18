"""Order pricing for a small inventory system."""
from __future__ import annotations


def total_price_before_tax(unit_price: float, quantity: int) -> float:
    if quantity < 0:
        raise ValueError("quantity must be non-negative")
    subtotal = unit_price * quantity
    return round(subtotal, 2)


def total_price_after_tax(unit_price: float, quantity: int, tax_rate: float) -> float:
    if quantity < 0:
        raise ValueError("quantity must be non-negative")
    subtotal = unit_price * quantity
    return round(subtotal * (1 + tax_rate), 2)
