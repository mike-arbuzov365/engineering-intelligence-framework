# T01: Implement a function from a written spec

`src/duration.py`'s `parse_duration(text)` is not implemented yet (it
raises `NotImplementedError`). Implement it according to its own
docstring:

Parse a duration like `1d2h30m15s` into total seconds. Format: one or
more `<digits><unit>` segments concatenated with no separator, unit one
of `d` (days, x86400), `h` (hours, x3600), `m` (minutes, x60), `s`
(seconds, x1). Segment order in the string does not matter for the
result. Raise `ValueError` if the string is empty, any unit is not one
of d/h/m/s, a unit repeats, or the string contains anything besides
valid `<digits><unit>` segments.

Make every test in `tests/test_duration.py` pass. Do not change the test
file.
