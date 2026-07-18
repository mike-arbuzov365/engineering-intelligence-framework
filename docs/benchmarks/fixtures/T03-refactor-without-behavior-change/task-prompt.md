# T03: Refactor without changing behavior

`src/inventory.py` has two functions, `total_price_before_tax` and
`total_price_after_tax`, that both repeat the same "validate quantity,
compute subtotal" logic. Extract the shared logic into a single helper
function used by both, **without changing either function's observable
behavior** - same return values for the same inputs, same exceptions
raised for the same invalid inputs.

Make every test in `tests/test_inventory.py` keep passing after the
refactor - they describe the exact behavior that must be preserved. Do
not change the test file.
