# T04: Add input validation

`src/division.py`'s `divide_evenly(total, parts)` docstring says it
"Raises ValueError if parts is not a positive integer" - but the
function doesn't actually do that yet: passing `parts=0` crashes with an
undocumented `ZeroDivisionError`, and passing a negative `parts` silently
returns a nonsensical result instead of raising anything.

Add the validation the docstring already promises, without changing the
correct behavior for valid inputs. Make every test in
`tests/test_division.py` pass. Do not change the test file.
