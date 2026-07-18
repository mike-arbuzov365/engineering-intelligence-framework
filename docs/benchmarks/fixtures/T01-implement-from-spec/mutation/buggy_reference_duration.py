"""Parses a compact duration string into total seconds."""
from __future__ import annotations

import re

# BUG: 'd' should multiply by 86400 (24*3600), not 3600 - this reference
# treats a day as if it were one hour, silently undercounting any
# duration that includes a days component.
_MULTIPLIERS = {"d": 3600, "h": 3600, "m": 60, "s": 1}
_SEGMENT_RE = re.compile(r"(\d+)([dhms])")


def parse_duration(text: str) -> int:
    """Parse a duration like '1d2h30m15s' into total seconds.

    Format: one or more '<digits><unit>' segments concatenated with no
    separator, unit one of d (days, x86400), h (hours, x3600), m
    (minutes, x60), s (seconds, x1). Segment order in the string does not
    matter for the result. Raises ValueError if the string is empty, any
    unit is not one of d/h/m/s, a unit repeats, or the string contains
    anything besides valid <digits><unit> segments.
    """
    if not text:
        raise ValueError("empty duration string")
    segments = _SEGMENT_RE.findall(text)
    reconstructed = "".join(f"{n}{u}" for n, u in segments)
    if reconstructed != text:
        raise ValueError(f"invalid duration string: {text!r}")
    seen_units: set[str] = set()
    total = 0
    for number, unit in segments:
        if unit in seen_units:
            raise ValueError(f"unit {unit!r} repeated in {text!r}")
        seen_units.add(unit)
        total += int(number) * _MULTIPLIERS[unit]
    return total
