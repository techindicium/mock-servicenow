from fastapi import APIRouter, HTTPException, Query, Request

from app.models import WorkNoteListResponse, WorkNoteRead

router = APIRouter()


def _row_to_work_note_read(row) -> WorkNoteRead:
    return WorkNoteRead(
        sys_id=row["sys_id"],
        incident_number=row["incident_number"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        note_type=row["note_type"],
        body=row["body"],
    )


@router.get(
    "/incidents/{number}/work_notes",
    response_model=WorkNoteListResponse,
)
def list_work_notes(
    number: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    conn = request.app.state.db_conn
    rows = conn.execute(
        "SELECT * FROM work_notes WHERE incident_number = ? "
        "ORDER BY created_at ASC, sys_id ASC "
        "LIMIT ? OFFSET ?",
        (number, page_size, (page - 1) * page_size),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM work_notes WHERE incident_number = ?", (number,)
    ).fetchone()["c"]
    return WorkNoteListResponse(
        items=[_row_to_work_note_read(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
