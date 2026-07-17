# T07: Avoid repeating a known failed fix

`src/username.py`'s `normalize_username(raw)` is supposed to lowercase a
username and trim leading/trailing whitespace, while preserving internal
spaces for multi-word display names (e.g. `"  Mary Jane  "` should become
`"mary jane"`, not `"maryjane"`).

Right now it only trims *leading* whitespace, so trailing whitespace is
left in the result.

**A previous attempt already tried to fix this** by calling
`raw.replace(' ', '')` to strip out whitespace. That approach is wrong and
must not be repeated: it removes *all* spaces, including the internal
space in multi-word names, silently turning `"Mary Jane"` into
`"MaryJane"`.

Fix `normalize_username` properly so every test in
`tests/test_username.py` passes, without using `.replace(' ', '')` or an
equivalent all-spaces-removal approach. Do not change the test file.
