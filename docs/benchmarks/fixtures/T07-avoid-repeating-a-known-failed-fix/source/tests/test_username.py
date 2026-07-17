import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from username import normalize_username


class TestNormalizeUsername(unittest.TestCase):
    def test_leading_whitespace(self):
        self.assertEqual(normalize_username("  alice"), "alice")

    def test_trailing_whitespace(self):
        self.assertEqual(normalize_username("bob  "), "bob")

    def test_leading_and_trailing_whitespace(self):
        self.assertEqual(normalize_username("  carol  "), "carol")

    def test_uppercase(self):
        self.assertEqual(normalize_username("DAVE"), "dave")

    def test_multiword_name_preserves_internal_space(self):
        self.assertEqual(normalize_username("  Mary Jane  "), "mary jane")

    def test_already_normalized(self):
        self.assertEqual(normalize_username("eve"), "eve")


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
