"""Name formatting for a small contacts app."""
from __future__ import annotations


def format_name(first: str, last: str) -> str:
    """Format a person's name as 'First Last'."""
    return f"{first} {last}"
