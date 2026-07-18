"""Splits a total into equal integer shares."""
from __future__ import annotations


def divide_evenly(total: int, parts: int) -> int:
    """Divide total into parts equal integer shares, discarding any
    remainder. Raises ValueError if parts is not a positive integer.
    """
    # BUG: only rejects exactly zero, not negative values - a plausible
    # "I added validation" fix that only handles the crash it happened
    # to notice (ZeroDivisionError) and misses the other invalid case
    # the spec also names (negative parts).
    if parts == 0:
        raise ValueError("parts must be a positive integer")
    return total // parts
