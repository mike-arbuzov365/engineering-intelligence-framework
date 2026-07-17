"""Username normalization for a small user-registry system."""
from __future__ import annotations


def normalize_username(raw: str) -> str:
    """Lowercase and trim leading/trailing whitespace, but preserve any
    internal spaces (multi-word display names are allowed)."""
    return raw.lstrip().lower()
