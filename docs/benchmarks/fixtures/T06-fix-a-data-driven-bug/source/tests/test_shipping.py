import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shipping import shipping_cost


class TestShippingCost(unittest.TestCase):
    def test_domestic_base_rate(self):
        self.assertEqual(shipping_cost("domestic", 1.0), 5.00)

    def test_regional_base_rate(self):
        self.assertEqual(shipping_cost("regional", 1.0), 12.00)

    def test_international_base_rate(self):
        self.assertEqual(shipping_cost("international", 1.0), 25.00)

    def test_domestic_extra_weight_surcharge(self):
        self.assertEqual(shipping_cost("domestic", 3.0), 9.00)

    def test_unknown_zone_raises(self):
        with self.assertRaises(ValueError):
            shipping_cost("moon", 1.0)

    def test_international_extra_weight(self):
        self.assertEqual(shipping_cost("international", 2.5), 28.00)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
