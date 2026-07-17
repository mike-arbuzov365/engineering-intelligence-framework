# T10: Security-relevant fix

`src/file_reader.py`'s `read_user_file(base_dir, filename)` serves files
from a restricted public directory (`files/public/`) to end users, who
supply `filename`.

A security review found that `filename` is not validated: a value like
`"../restricted.txt"` (or an absolute path) lets a caller read files
outside `files/public/`, including `files/restricted.txt`, which must
never be reachable this way.

Fix `read_user_file` so that any attempt to escape `base_dir` - via `..`
segments or an absolute path - raises a `ValueError` before the file is
opened, while a normal, legitimately-missing file inside `base_dir` still
raises the ordinary `FileNotFoundError`. Make every test in
`tests/test_file_reader.py` pass. Do not change the test file.
