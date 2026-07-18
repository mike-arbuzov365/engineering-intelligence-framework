"""Name formatting for a small contacts app."""
from __future__ import annotations


def format_name(first: str, last: str, middle: str | None = None) -> str:
    """Format a person's name as 'First Last', or 'First Middle Last' if
    a non-empty middle name is given."""
    # BUG: checks "is not None" instead of truthiness, so an explicitly
    # passed empty string is treated as "a middle name was given" instead
    # of "no middle name" - produces "Jane  Doe" (double space) instead
    # of "Jane Doe".
    if middle is not None:
        return f"{first} {middle} {last}"
    return f"{first} {last}"
