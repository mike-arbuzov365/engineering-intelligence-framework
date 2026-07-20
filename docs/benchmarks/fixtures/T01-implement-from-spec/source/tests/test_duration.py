import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from duration import parse_duration


class TestParseDuration(unittest.TestCase):
    def test_single_seconds(self):
        self.assertEqual(parse_duration("90s"), 90)

    def test_single_days(self):
        self.assertEqual(parse_duration("2d"), 172800)

    def test_two_units(self):
        self.assertEqual(parse_duration("1h30m"), 5400)

    def test_all_four_units_combined(self):
        self.assertEqual(parse_duration("1d2h30m15s"), 95415)

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            parse_duration("")

    def test_unrecognized_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_duration("5x")


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
