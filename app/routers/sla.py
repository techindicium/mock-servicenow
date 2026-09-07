from fastapi import APIRouter, Request

from app.models import PaginatedTaskSla, TaskSlaRead

router = APIRouter()


def _row_to_task_sla_read(row) -> TaskSlaRead:
    return TaskSlaRead(
        sys_id=row["sys_id"],
        incident_number=row["incident_number"],
        sla_definition=row["sla_definition"],
        target_minutes=row["target_minutes"],
        actual_minutes=row["actual_minutes"],
        has_breached=bool(row["has_breached"]),
        business_time_only=bool(row["business_time_only"]),
    )


@router.get("/sla", response_model=PaginatedTaskSla)
def list_sla_records(request: Request, page: int = 1, page_size: int = 50):
    conn = request.app.state.db_conn
    total = conn.execute("SELECT COUNT(*) AS c FROM task_sla").fetchone()["c"]
    rows = conn.execute(
        "SELECT * FROM task_sla ORDER BY sys_id ASC LIMIT ? OFFSET ?",
        (page_size, (page - 1) * page_size),
    ).fetchall()
    items = [_row_to_task_sla_read(r) for r in rows]
    return PaginatedTaskSla(items=items, page=page, page_size=page_size, total=total)
