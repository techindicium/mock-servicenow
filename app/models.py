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


# sla-records.plan.md Task 1 (extends this charter-wide foundation file): TaskSla models.
SLA_DEFINITIONS = ("first_response", "resolution")


class TaskSlaRead(BaseModel):
    sys_id: str
    incident_number: str
    sla_definition: Literal["first_response", "resolution"]
    target_minutes: int
    actual_minutes: int | None
    has_breached: bool
    business_time_only: bool


class PaginatedTaskSla(BaseModel):
    items: list[TaskSlaRead]
    page: int
    page_size: int
    total: int


class AssignmentGroupRead(BaseModel):
    name: str


class SysUserRead(BaseModel):
    name: str
    role: str
    assignment_group: str | None = None


class PaginatedAssignmentGroups(BaseModel):
    items: list[AssignmentGroupRead]
    page: int
    page_size: int
    total: int


class PaginatedUsers(BaseModel):
    items: list[SysUserRead]
    page: int
    page_size: int
    total: int


class EscalationRead(BaseModel):
    number: str
    incident_number: str | None
    account_id: str
    summary: str
    opened_at: str
    closed_at: str | None
    owner: str | None


class EscalationPatch(BaseModel):
    # Deliberately no `number`, `account_id`, `opened_at`, or `incident_number` field — this is
    # the structural enforcement of the immutable-fields list (see escalations router's PATCH):
    # Pydantic drops unknown extra keys silently, so there is no path for them to reach the
    # UPDATE statement.
    summary: str | None = None
    owner: str | None = None
    closed_at: str | None = None


class EscalationPage(BaseModel):
    items: list[EscalationRead]
    page: int
    page_size: int
    total: int
