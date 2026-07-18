# T09: Add an optional parameter without breaking existing callers

`src/greeting.py`'s `format_name(first, last)` only supports first and
last names. Add support for an optional middle name, **without breaking
any existing 2-argument call** - `format_name("Jane", "Doe")` must keep
returning exactly `"Jane Doe"`.

When a non-empty middle name is given (positionally or as
`middle=...`), format as `"First Middle Last"`. When `middle` is `None`,
omitted, or an empty string, format as `"First Last"` - the same as
today.

Make every test in `tests/test_greeting.py` pass. Do not change the test
file.
