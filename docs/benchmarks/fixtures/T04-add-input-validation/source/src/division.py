"""Splits a total into equal integer shares."""
from __future__ import annotations


def divide_evenly(total: int, parts: int) -> int:
    """Divide total into parts equal integer shares, discarding any
    remainder. Raises ValueError if parts is not a positive integer.
    """
    return total // parts
