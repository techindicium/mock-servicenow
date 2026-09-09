from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.db import next_escalation_number
from app.models import EscalationCreate, EscalationPage, EscalationPatch, EscalationRead

router = APIRouter()

_PATCHABLE_FIELDS = ("summary", "owner", "closed_at")


def _row_to_escalation_read(row) -> EscalationRead:
    return EscalationRead(
        number=row["number"],
        incident_number=row["incident_number"],
        account_id=row["account_id"],
        summary=row["summary"],
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
        owner=row["owner"],
    )


@router.get("/escalations", response_model=EscalationPage)
def list_escalations(
    request: Request,
    account_id: str | None = None,
    open_only: bool | None = None,
    page: int = 1,
    page_size: int = 50,
):
    conn = request.app.state.db_conn
    where: list[str] = []
    params: list = []
    if account_id is not None:
        where.append("account_id = ?")
        params.append(account_id)
    if open_only:
        where.append("closed_at IS NULL")
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM escalations {clause}", params
    ).fetchone()["c"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM escalations {clause} ORDER BY number ASC LIMIT ? OFFSET ?",
        (*params, page_size, offset),
    ).fetchall()
    return EscalationPage(
        items=[_row_to_escalation_read(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/escalations/{number}", response_model=EscalationRead)
def get_escalation(number: str, request: Request):
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Escalation {number} not found", "code": "ESCALATION_NOT_FOUND"},
        )
    return _row_to_escalation_read(row)


@router.post("/escalations", response_model=EscalationRead, status_code=201)
def create_escalation(payload: EscalationCreate, request: Request):
    conn = request.app.state.db_conn
    number = next_escalation_number(conn)
    opened_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO escalations
            (number, incident_number, account_id, summary, opened_at, closed_at, owner)
        VALUES (?, ?, ?, ?, ?, NULL, ?)
        """,
        (number, payload.incident_number, payload.account_id, payload.summary, opened_at,
         payload.owner),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    return _row_to_escalation_read(row)


@router.patch("/escalations/{number}", response_model=EscalationRead)
def patch_escalation(number: str, payload: EscalationPatch, request: Request):
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Escalation {number} not found", "code": "ESCALATION_NOT_FOUND"},
        )

    updates = payload.model_dump(exclude_unset=True)
    set_clauses = [f"{field} = ?" for field in _PATCHABLE_FIELDS if field in updates]
    values = [updates[field] for field in _PATCHABLE_FIELDS if field in updates]
    if set_clauses:
        conn.execute(
            f"UPDATE escalations SET {', '.join(set_clauses)} WHERE number = ?",
            (*values, number),
        )
        conn.commit()

    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    return _row_to_escalation_read(row)
