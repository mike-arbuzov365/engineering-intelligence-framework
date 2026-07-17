import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pricing import apply_tier_discount


class TestApplyTierDiscount(unittest.TestCase):
    def test_below_tier_no_discount(self):
        self.assertEqual(apply_tier_discount(5, 10.0), 50.0)

    def test_tier_one_lower_boundary(self):
        self.assertEqual(apply_tier_discount(10, 10.0), 90.0)

    def test_tier_one_upper_boundary(self):
        self.assertEqual(apply_tier_discount(49, 10.0), 49 * 10.0 * 0.9)

    def test_tier_two_exact_boundary(self):
        self.assertEqual(apply_tier_discount(50, 10.0), 50 * 10.0 * 0.8)

    def test_tier_two_above_boundary(self):
        self.assertEqual(apply_tier_discount(75, 10.0), 75 * 10.0 * 0.8)

    def test_zero_quantity(self):
        self.assertEqual(apply_tier_discount(0, 10.0), 0.0)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
