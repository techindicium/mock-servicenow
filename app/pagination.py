# Charter-wide foundation file (see plan header's pagination-envelope note under SA-3). Every
# list endpoint in this charter returns the identical {"items", "page", "page_size", "total"}
# envelope; this module is the one shared implementation for endpoints that page an
# already-fetched, small, in-memory row list (e.g. user-directory's `/users`/`/assignment_groups`)
# rather than pushing LIMIT/OFFSET into SQL, which is what GET /incidents (Task 2, this spec) and
# GET /sla (sla-records.plan.md) do instead for their larger row counts — both approaches produce
# the same envelope shape.
from fastapi import Query


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
    ):
        self.page = page
        self.page_size = page_size


def paginate_rows(rows: list, page: int, page_size: int) -> tuple[list, int]:
    total = len(rows)
    start = (page - 1) * page_size
    return rows[start : start + page_size], total
