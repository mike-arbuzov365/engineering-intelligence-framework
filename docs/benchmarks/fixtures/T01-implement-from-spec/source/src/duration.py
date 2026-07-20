"""Parses a compact duration string into total seconds."""
from __future__ import annotations


def parse_duration(text: str) -> int:
    """Parse a duration like '1d2h30m15s' into total seconds.

    Format: one or more '<digits><unit>' segments concatenated with no
    separator, unit one of d (days, x86400), h (hours, x3600), m
    (minutes, x60), s (seconds, x1). Segment order in the string does not
    matter for the result. Raises ValueError if the string is empty, any
    unit is not one of d/h/m/s, a unit repeats, or the string contains
    anything besides valid <digits><unit> segments (e.g. missing digits,
    stray characters, or leftover unmatched text).
    """
    raise NotImplementedError
