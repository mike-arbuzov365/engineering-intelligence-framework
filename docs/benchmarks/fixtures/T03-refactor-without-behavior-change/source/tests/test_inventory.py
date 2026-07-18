import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from inventory import total_price_after_tax, total_price_before_tax


class TestInventory(unittest.TestCase):
    def test_before_tax_normal_case(self):
        self.assertEqual(total_price_before_tax(9.994, 3), 29.98)

    def test_before_tax_negative_quantity_raises(self):
        with self.assertRaises(ValueError):
            total_price_before_tax(10.0, -1)

    def test_after_tax_normal_case(self):
        self.assertEqual(total_price_after_tax(10.0, 2, 0.10), 22.0)

    def test_after_tax_negative_quantity_raises(self):
        with self.assertRaises(ValueError):
            total_price_after_tax(10.0, -1, 0.10)

    def test_after_tax_zero_rate_matches_before_tax(self):
        self.assertEqual(
            total_price_after_tax(12.5, 4, 0.0),
            total_price_before_tax(12.5, 4),
        )

    def test_before_tax_rounds_to_two_decimals(self):
        self.assertEqual(total_price_before_tax(0.1, 3), 0.3)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
