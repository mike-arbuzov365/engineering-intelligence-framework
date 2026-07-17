import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from file_reader import read_user_file

FILES_ROOT = Path(__file__).resolve().parents[1] / "files"
PUBLIC_DIR = FILES_ROOT / "public"


class TestReadUserFile(unittest.TestCase):
    def test_reads_a_normal_file(self):
        content = read_user_file(str(PUBLIC_DIR), "welcome.txt")
        self.assertIn("Welcome!", content)

    def test_blocks_simple_parent_traversal(self):
        with self.assertRaises(ValueError):
            read_user_file(str(PUBLIC_DIR), "../restricted.txt")

    def test_blocks_nested_parent_traversal(self):
        # Deliberately targets a real fixture file two levels up (not a
        # real OS path like /etc/passwd) so the expected failure mode -
        # ValueError from the path-containment check - is deterministic
        # on every platform, rather than depending on whether some
        # unrelated absolute system path happens to exist.
        with self.assertRaises(ValueError):
            read_user_file(str(PUBLIC_DIR), "../../restricted.txt")

    def test_blocks_absolute_path_escape(self):
        # An absolute path handed to os.path.join replaces base_dir
        # entirely on POSIX - must still be rejected.
        restricted_abs = str((FILES_ROOT / "restricted.txt").resolve())
        with self.assertRaises(ValueError):
            read_user_file(str(PUBLIC_DIR), restricted_abs)

    def test_missing_file_still_raises_file_not_found_not_value_error(self):
        # A legitimately-missing file within the sandbox should NOT be
        # miscategorized as a traversal attempt.
        with self.assertRaises(FileNotFoundError):
            read_user_file(str(PUBLIC_DIR), "does-not-exist.txt")


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"EIF-BENCHMARK-RESULT: passed={passed} total={total}")
    raise SystemExit(0 if passed == total else 1)
