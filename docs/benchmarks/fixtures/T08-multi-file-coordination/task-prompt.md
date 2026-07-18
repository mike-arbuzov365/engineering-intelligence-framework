# T08: Fix an inconsistency across two functions

`src/pricing_rules.py` defines the member discount rate
(`MEMBER_DISCOUNT_RATE = 0.15`, 15% off) and `apply_member_discount()`,
which `src/checkout.py`'s `compute_order_total()` correctly uses.

But `src/checkout.py`'s `compute_single_item_price()` has its own,
different hardcoded discount rate - members are getting the wrong
discount when buying a single item versus a full order. Fix
`compute_single_item_price()` so it applies the *same* member discount
rate as `compute_order_total()` (ideally by using the shared
`pricing_rules.py` logic directly, so the two can never drift apart
again).

Make every test in `tests/test_checkout.py` pass. Do not change the test
file.
