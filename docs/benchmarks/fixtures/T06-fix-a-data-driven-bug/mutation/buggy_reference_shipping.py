"""Shipping cost calculation for a small storefront."""
from __future__ import annotations

_ZONE_RATES = {
    "domestic": 5.00,
    "regional": 12.00,
    "international": 21.00,
}


def shipping_cost(zone: str, weight_kg: float) -> float:
    """Base rate for the zone plus $2/kg for weight over 1kg.

    Raises ValueError for an unrecognized zone.
    """
    if zone not in _ZONE_RATES:
        raise ValueError(f"unknown shipping zone: {zone!r}")
    base = _ZONE_RATES[zone]
    extra_weight = max(0.0, weight_kg - 1.0)
    return round(base + extra_weight * 2.0, 2)
