import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from checkout import compute_order_total, compute_single_item_price
from pricing_rules import apply_member_discount


class TestCheckout(unittest.TestCase):
    def test_non_member_order_total(self):
        self.assertEqual(compute_order_total([10.0, 20.0], False), 30.0)

    def test_member_order_total(self):
        self.assertEqual(compute_order_total([10.0, 20.0], True), 25.50)

    def test_non_member_single_item(self):
        self.assertEqual(compute_single_item_price(50.0, False), 50.0)

    def test_member_single_item(self):
        self.assertEqual(compute_single_item_price(50.0, True), 42.50)

    def test_single_item_and_order_total_agree_on_discount_rate(self):
        self.assertEqual(
            compute_single_item_price(30.0, True),
            compute_order_total([30.0], True),
        )

    def test_shared_discount_helper_directly(self):
        self.assertEqual(apply_member_discount(100.0), 85.0)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
