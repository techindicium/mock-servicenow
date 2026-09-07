from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.models import (
    AssignmentGroupRead,
    PaginatedAssignmentGroups,
    PaginatedUsers,
    SysUserRead,
)
from app.pagination import PageParams, paginate_rows

router = APIRouter()


@router.get("/assignment_groups", response_model=PaginatedAssignmentGroups)
def list_assignment_groups(
    request: Request, page_params: Annotated[PageParams, Depends()]
):
    conn = request.app.state.db_conn
    rows = conn.execute("SELECT * FROM assignment_group ORDER BY name ASC").fetchall()
    items, total = paginate_rows(rows, page_params.page, page_params.page_size)
    return PaginatedAssignmentGroups(
        items=[AssignmentGroupRead(name=r["name"]) for r in items],
        page=page_params.page,
        page_size=page_params.page_size,
        total=total,
    )


@router.get("/users", response_model=PaginatedUsers)
def list_users(request: Request, page_params: Annotated[PageParams, Depends()]):
    conn = request.app.state.db_conn
    rows = conn.execute("SELECT * FROM sys_user ORDER BY name ASC").fetchall()
    items, total = paginate_rows(rows, page_params.page, page_params.page_size)
    return PaginatedUsers(
        items=[
            SysUserRead(name=r["name"], role=r["role"], assignment_group=r["assignment_group"])
            for r in items
        ],
        page=page_params.page,
        page_size=page_params.page_size,
        total=total,
    )
