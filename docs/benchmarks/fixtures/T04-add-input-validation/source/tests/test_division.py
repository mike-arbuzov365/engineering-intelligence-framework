import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from division import divide_evenly


class TestDivideEvenly(unittest.TestCase):
    def test_normal_case(self):
        self.assertEqual(divide_evenly(10, 3), 3)

    def test_exact_division(self):
        self.assertEqual(divide_evenly(12, 4), 3)

    def test_discards_remainder(self):
        self.assertEqual(divide_evenly(7, 2), 3)

    def test_zero_total(self):
        self.assertEqual(divide_evenly(0, 5), 0)

    def test_zero_parts_raises_value_error(self):
        with self.assertRaises(ValueError):
            divide_evenly(10, 0)

    def test_negative_parts_raises_value_error(self):
        with self.assertRaises(ValueError):
            divide_evenly(10, -1)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
