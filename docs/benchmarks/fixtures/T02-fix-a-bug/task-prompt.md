# T02: Fix a bug

`src/pricing.py`'s `apply_tier_discount(quantity, unit_price)` is supposed
to implement this bulk-discount schedule:

- Fewer than 10 units: no discount.
- 10 to 49 units (inclusive): 10% off.
- 50 units or more: 20% off.

Some callers are reporting that ordering exactly 50 units gives the wrong
price. Find and fix the bug in `src/pricing.py` so that every test in
`tests/test_pricing.py` passes. Do not change the test file.
