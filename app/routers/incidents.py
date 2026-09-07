from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.db import next_incident_number
from app.models import INCIDENT_STATES, IncidentCreate, IncidentPage, IncidentRead

router = APIRouter()


def _row_to_incident(row) -> IncidentRead:
    return IncidentRead(
        number=row["number"], account_id=row["account_id"], category=row["category"],
        short_description=row["short_description"], description=row["description"],
        state=row["state"], priority=row["priority"], opened_at=row["opened_at"],
        resolved_at=row["resolved_at"], assigned_to=row["assigned_to"],
        assignment_group=row["assignment_group"], escalated=bool(row["escalated"]),
    )


def _parse_iso(value: str, field: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"message": f"{field} is not a valid ISO timestamp", "code": "VALIDATION_ERROR"},
        )
    return value


def _parse_bool(value: str, field: str) -> bool:
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    raise HTTPException(
        status_code=422,
        detail={"message": f"{field} must be one of: true, false", "code": "VALIDATION_ERROR"},
    )


@router.get("/incidents", response_model=IncidentPage)
def list_incidents(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    account_id: str | None = None,
    state: str | None = None,
    category: str | None = None,
    opened_after: str | None = None,
    opened_before: str | None = None,
    escalated: str | None = None,
):
    if state is not None and state not in INCIDENT_STATES:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"state must be one of: {', '.join(INCIDENT_STATES)}",
                "code": "VALIDATION_ERROR",
            },
        )
    escalated_bool = _parse_bool(escalated, "escalated") if escalated is not None else None
    if opened_after is not None:
        _parse_iso(opened_after, "opened_after")
    if opened_before is not None:
        _parse_iso(opened_before, "opened_before")

    conn = request.app.state.db_conn
    query = "SELECT * FROM incidents WHERE 1=1"
    params: list = []
    if account_id is not None:
        query += " AND account_id = ?"
        params.append(account_id)
    if state is not None:
        query += " AND state = ?"
        params.append(state)
    if category is not None:
        query += " AND category = ?"
        params.append(category)
    if opened_after is not None:
        query += " AND opened_at >= ?"
        params.append(opened_after)
    if opened_before is not None:
        query += " AND opened_at < ?"
        params.append(opened_before)
    if escalated_bool is not None:
        query += " AND escalated = ?"
        params.append(1 if escalated_bool else 0)

    total = conn.execute(
        query.replace("SELECT *", "SELECT COUNT(*) AS c", 1), params
    ).fetchone()["c"]
    query += " ORDER BY number ASC LIMIT ? OFFSET ?"
    params.extend([page_size, (page - 1) * page_size])
    rows = conn.execute(query, params).fetchall()

    return IncidentPage(
        items=[_row_to_incident(r) for r in rows], page=page, page_size=page_size, total=total
    )


@router.get("/incidents/{number}", response_model=IncidentRead)
def get_incident(number: str, request: Request):
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM incidents WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Incident {number} not found", "code": "INCIDENT_NOT_FOUND"},
        )
    return _row_to_incident(row)


@router.post("/incidents", response_model=IncidentRead, status_code=201)
def create_incident(payload: IncidentCreate, request: Request):
    conn = request.app.state.db_conn
    number = next_incident_number(conn)
    opened_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO incidents
            (number, account_id, category, short_description, description, state,
             priority, opened_at, resolved_at, assigned_to, assignment_group, escalated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            number, payload.account_id, payload.category, payload.short_description,
            payload.description, payload.state, payload.priority, opened_at,
            payload.resolved_at, payload.assigned_to, payload.assignment_group,
            1 if payload.escalated else 0,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM incidents WHERE number = ?", (number,)).fetchone()
    return _row_to_incident(row)
