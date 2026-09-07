# Charter-wide foundation file (see plan header): this task defines only the Incident models
# below. Each sibling itsm-api plan's own Task 1 (work-notes, escalations, sla-records,
# user-directory) appends its own entity's models to this same file — extending it, never
# recreating it.
from typing import Literal

from pydantic import BaseModel

INCIDENT_STATES = ("new", "in_progress", "on_hold", "resolved", "closed")


class IncidentCreate(BaseModel):
    account_id: str
    category: str
    short_description: str
    description: str
    state: Literal["new", "in_progress", "on_hold", "resolved", "closed"]
    priority: Literal[1, 2, 3, 4]
    escalated: bool = False
    resolved_at: str | None = None
    assigned_to: str | None = None
    assignment_group: str | None = None


class IncidentRead(BaseModel):
    number: str
    account_id: str
    category: str
    short_description: str
    description: str
    state: str
    priority: int
    opened_at: str
    resolved_at: str | None
    assigned_to: str | None
    assignment_group: str | None
    escalated: bool


class IncidentPatch(BaseModel):
    # Deliberately no `number`, `account_id`, or `opened_at` field — this is the structural
    # enforcement of those three being immutable (see Task 5): Pydantic drops unknown extra
    # keys silently, so there is no path for them to reach the UPDATE statement.
    state: Literal["new", "in_progress", "on_hold", "resolved", "closed"] | None = None
    priority: Literal[1, 2, 3, 4] | None = None
    assigned_to: str | None = None
    assignment_group: str | None = None


class IncidentPage(BaseModel):
    items: list[IncidentRead]
    page: int
    page_size: int
    total: int
