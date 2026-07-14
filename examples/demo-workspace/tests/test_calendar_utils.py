"""Behavioral test for the vertical-slice demo task.

Uses only the Python standard library (unittest) - no extra dependency to
install, on top of scripts/requirements.txt, to run this demo.

Run with:
    python -m unittest examples/demo-workspace/tests/test_calendar_utils.py -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calendar_utils import is_leap_year  # noqa: E402


class TestIsLeapYear(unittest.TestCase):
    def test_ordinary_non_leap_year(self):
        self.assertFalse(is_leap_year(2023))

    def test_ordinary_leap_year(self):
        self.assertTrue(is_leap_year(2024))

    def test_century_year_not_divisible_by_400_is_not_leap(self):
        # This is the case a naive "year % 4 == 0" check gets wrong.
        self.assertFalse(is_leap_year(1900))
        self.assertFalse(is_leap_year(2100))

    def test_century_year_divisible_by_400_is_leap(self):
        self.assertTrue(is_leap_year(2000))
        self.assertTrue(is_leap_year(1600))


if __name__ == "__main__":
    unittest.main()
