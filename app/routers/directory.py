from fastapi import APIRouter, Depends, Request

from app.models import AssignmentGroupRead, PaginatedAssignmentGroups
from app.pagination import PageParams, paginate_rows

router = APIRouter()


@router.get("/assignment_groups", response_model=PaginatedAssignmentGroups)
def list_assignment_groups(request: Request, page_params: PageParams = Depends()):
    conn = request.app.state.db_conn
    rows = conn.execute("SELECT * FROM assignment_group ORDER BY name ASC").fetchall()
    items, total = paginate_rows(rows, page_params.page, page_params.page_size)
    return PaginatedAssignmentGroups(
        items=[AssignmentGroupRead(name=r["name"]) for r in items],
        page=page_params.page,
        page_size=page_params.page_size,
        total=total,
    )
