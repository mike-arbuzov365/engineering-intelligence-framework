# T06: Fix a data-driven bug

`src/shipping.py`'s `shipping_cost(zone, weight_kg)` computes a zone's
base rate plus a per-kg surcharge for weight over 1kg. Customers shipping
to the `international` zone are being charged the wrong base rate - it
should be $25.00, not whatever `_ZONE_RATES` currently has for that zone.

The bug is in the data (the rate table), not the calculation logic. Find
and fix it so that every test in `tests/test_shipping.py` passes. Do not
change the test file.
