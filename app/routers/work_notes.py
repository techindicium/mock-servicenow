import sqlite3

from fastapi import APIRouter, HTTPException, Query, Request

from app.db import allocate_work_note_sys_id
from app.models import WorkNoteCreate, WorkNoteListResponse, WorkNoteRead

router = APIRouter()

_MAX_SYS_ID_RETRIES = 5


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
    incident = conn.execute(
        "SELECT 1 FROM incidents WHERE number = ?", (number,)
    ).fetchone()
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"Incident {number} not found",
                "code": "INCIDENT_NOT_FOUND",
            },
        )

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


@router.post(
    "/incidents/{number}/work_notes",
    response_model=WorkNoteRead,
    status_code=201,
)
def create_work_note(number: str, payload: WorkNoteCreate, request: Request):
    conn = request.app.state.db_conn
    incident = conn.execute(
        "SELECT 1 FROM incidents WHERE number = ?", (number,)
    ).fetchone()
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"Incident {number} not found",
                "code": "INCIDENT_NOT_FOUND",
            },
        )

    # No authorship/business-rule guard here — payload.created_by is trusted as-is, per
    # constitution Principle 5 and spec BEH-4. Structural validation (note_type enum,
    # required fields) is still enforced by Pydantic on WorkNoteCreate.
    last_error = None
    sys_id = None
    for _ in range(_MAX_SYS_ID_RETRIES):
        sys_id = allocate_work_note_sys_id(conn)
        try:
            conn.execute(
                "INSERT INTO work_notes "
                "(sys_id, incident_number, created_by, note_type, body) "
                "VALUES (?, ?, ?, ?, ?)",
                (sys_id, number, payload.created_by, payload.note_type, payload.body),
            )
            conn.commit()
            break
        except sqlite3.IntegrityError as exc:
            last_error = exc
            continue
    else:
        raise RuntimeError(
            f"Could not allocate a unique WorkNote sys_id after "
            f"{_MAX_SYS_ID_RETRIES} attempts"
        ) from last_error

    row = conn.execute("SELECT * FROM work_notes WHERE sys_id = ?", (sys_id,)).fetchone()
    return _row_to_work_note_read(row)
