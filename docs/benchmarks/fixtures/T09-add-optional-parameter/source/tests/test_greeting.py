import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from greeting import format_name


class TestFormatName(unittest.TestCase):
    def test_existing_two_arg_call_still_works(self):
        self.assertEqual(format_name("Jane", "Doe"), "Jane Doe")

    def test_new_middle_name_call(self):
        self.assertEqual(format_name("Jane", "Doe", "Marie"), "Jane Marie Doe")

    def test_explicit_none_middle_behaves_like_omitted(self):
        self.assertEqual(format_name("Jane", "Doe", middle=None), "Jane Doe")

    def test_keyword_style_two_arg_call(self):
        self.assertEqual(format_name(first="Jane", last="Doe"), "Jane Doe")

    def test_empty_string_middle_treated_like_none(self):
        self.assertEqual(format_name("Jane", "Doe", ""), "Jane Doe")

    def test_middle_name_via_keyword(self):
        self.assertEqual(format_name("Jane", "Doe", middle="Marie"), "Jane Marie Doe")


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
