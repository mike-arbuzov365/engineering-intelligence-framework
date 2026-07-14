---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: official_specification
confidence: high
created: 2026-07-15
review_after: 2027-07-15
---

# Gregorian calendar leap-year rule

A year is a leap year if and only if:

- it is divisible by 4, **and**
- it is not divisible by 100, **unless** it is also divisible by 400.

Examples: 2024 is a leap year (divisible by 4, not by 100). 1900 is not a
leap year (divisible by 100, not by 400). 2000 is a leap year (divisible
by 400).

This is the rule as defined by the Gregorian calendar reform (1582); it is
the rule essentially all modern date libraries implement.
