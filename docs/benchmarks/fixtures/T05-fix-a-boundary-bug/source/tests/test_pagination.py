import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pagination import paginate


class TestPaginate(unittest.TestCase):
    def test_first_full_page(self):
        self.assertEqual(paginate(list(range(1, 11)), 1, 3), [1, 2, 3])

    def test_second_full_page(self):
        self.assertEqual(paginate(list(range(1, 11)), 2, 3), [4, 5, 6])

    def test_last_partial_page(self):
        self.assertEqual(paginate(list(range(1, 11)), 4, 3), [10])

    def test_page_beyond_range_is_empty(self):
        self.assertEqual(paginate(list(range(1, 11)), 5, 3), [])

    def test_page_size_exactly_divides_total(self):
        self.assertEqual(paginate(list(range(1, 7)), 2, 3), [4, 5, 6])

    def test_single_item_page_size(self):
        self.assertEqual(paginate([1, 2, 3], 2, 1), [2])


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
