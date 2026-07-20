"""Order pricing for a small inventory system."""
from __future__ import annotations


def _subtotal(unit_price: float, quantity: int) -> float:
    # BUG: the extracted helper dropped the negative-quantity validation
    # both original functions had - a plausible-looking "refactor" that
    # silently changes behavior instead of preserving it.
    return unit_price * quantity


def total_price_before_tax(unit_price: float, quantity: int) -> float:
    return round(_subtotal(unit_price, quantity), 2)


def total_price_after_tax(unit_price: float, quantity: int, tax_rate: float) -> float:
    return round(_subtotal(unit_price, quantity) * (1 + tax_rate), 2)
