"""Pagination for a small listing endpoint."""
from __future__ import annotations


def paginate(items: list, page: int, page_size: int) -> list:
    """Return the 1-indexed page of items, page_size items per page.

    page 1 is the first page_size items, page 2 the next page_size, and
    so on. A page beyond the end of items returns an empty list.
    """
    start = (page - 1) * page_size
    end = start + page_size - 1
    return items[start:end]
