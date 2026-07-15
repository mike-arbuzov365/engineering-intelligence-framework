---
type: failure_pattern
status: validated
scope: project
evidence: OBSERVED
source: official_specification
confidence: high
created: 2026-07-15
review_after: 2027-07-15
related:
  - ../facts/FACT-0001-gregorian-leap-year-rule.md
---

# Naive leap-year check (`year % 4 == 0`) fails on non-400 century years

The obvious, plausible-looking implementation of a leap-year check is:

```python
def is_leap_year(year):
    return year % 4 == 0
```

This is wrong. The Gregorian calendar rule (see
[`FACT-0001`](../facts/FACT-0001-gregorian-leap-year-rule.md)) has a
century exception: a year divisible by 100 is **not** a leap year unless
it is also divisible by 400.

## Concrete failure

- `is_leap_year(1900)` returns `True` under the naive check. The correct
  answer is `False` - 1900 is divisible by 100 but not by 400.
- `is_leap_year(2000)` happens to return the right answer (`True`) under
  the naive check, which is exactly what makes this bug easy to miss in
  testing that only covers "recent" years - 2000 is divisible by 400, so
  it doesn't exercise the exception at all.

## Detection signal

Any `is_leap_year`-shaped function that does not special-case years
divisible by 100 is this pattern. A test suite that only checks
non-century years (or only checks 2000) will not catch it.

## Correct implementation

```python
def is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
```

## Prevention

A test case for at least one century year not divisible by 400 (1900,
1800, 1700, 2100, ...) is required whenever this logic is implemented or
touched, not just a test for a recent, divisible-by-400 year like 2000.
