# T05: Fix a boundary bug

`src/pagination.py`'s `paginate(items, page, page_size)` is supposed to
return the requested 1-indexed page of `page_size` items - page 1 the
first `page_size` items, page 2 the next `page_size`, and so on, with a
page beyond the end of `items` returning an empty list.

Some callers are reporting that every page is missing its last item.
Find and fix the boundary bug in `src/pagination.py` so that every test
in `tests/test_pagination.py` passes. Do not change the test file.
