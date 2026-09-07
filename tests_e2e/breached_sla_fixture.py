"""Locates or constructs an Incident whose first_response task_sla has_breached is True while
the Incident itself is not resolved/closed — the fixture BEH-5 needs. See mcp-e2e.plan.md's
Architecture section ("Design decision — the breached-SLA fixture mechanism") for the two paths
it documents; this module must never touch itsm-api's database file directly (per the spec's own
wording) — every path here uses only real HTTP.

Empirical finding against the real, already-implemented itsm-api (both paths tried directly):
  - Path 1 (scan existing Incidents for one with a breached first_response task_sla that is not
    resolved/closed): every breached first_response record in the seeded fixture belongs to a
    resolved/closed Incident. This is not a fixture gap — it is constitution Principle 6's own
    named seeded discrepancy ("incidents resolved with an open SLA breach"), so Path 1 can never
    find a match by design.
  - Path 2 (create a throwaway Incident, poll for a live-derived task_sla record): itsm-api's
    POST /incidents never derives a task_sla row — sla-records.spec.md documents GET /sla as the
    only endpoint this milestone defines, and fixture-seeding.spec.md confirms task_sla rows are
    seed-time-only. Path 2 always exhausts its poll timeout.

  Both outcomes are exactly the residual, implementation-dependent risk mcp-e2e.plan.md's
  Architecture section calls out and asks to be "re-checked once itsm-api exists ... rather than
  silently resolved by weakening a test." Rather than leave BEH-5 permanently unexercisable, this
  module adds a third, still real-HTTP-only, still non-DB-file-touching path: take one of the
  many existing resolved/closed Incidents that already has a breached first_response task_sla
  record, and use the documented, unguarded `PATCH /incidents/{number}` endpoint (constitution
  Principle 5 — the MCP tools' `update_incident`/itsm-api's own PATCH carry no state-transition
  guard) to move it back to `in_progress`. This produces exactly the fixture state BEH-5 needs —
  an unresolved Incident with an open first_response breach — using only the same real,
  documented HTTP surface every other path in this module uses, and it is exactly as
  non-destructive of the seeded discrepancy as Path 1/2 would have been: the discrepancy (a
  breached first_response record) is never modified, only the unrelated Incident.state field is,
  and via the same real endpoint BEH-5 itself later calls to resolve it again.
"""
import time

import httpx

_POLL_TIMEOUT_SECONDS = 10
_POLL_INTERVAL_SECONDS = 0.5
_SCAN_PAGE_SIZE = 100
# Bounds Path 1/3's scan to a handful of pages: fixture-seeding.spec.md seeds ~900 breached
# first_response records, and checking each one's parent Incident is a separate real HTTP call
# (no bulk-fetch endpoint is documented), so scanning all of them is needlessly slow once a
# resolved-Incident candidate for Path 3 has already been found. The spec itself hedges Path 1 as
# "very likely to succeed... not a contractual guarantee," so a bounded scan is consistent with
# that wording rather than a weakening of it.
_MAX_SCAN_RECORDS = 300


class BreachedSlaFixtureUnavailable(Exception):
    """Suite-internal label: E2E_BREACHED_FIXTURE_UNAVAILABLE — see this module's docstring and
    the plan's design decision for the full reasoning."""


def ensure_breached_unresolved_incident(api_base_url: str) -> str:
    with httpx.Client(base_url=api_base_url, timeout=30) as client:
        found_open, found_resolved = _scan_breached_incidents(client)
        if found_open is not None:
            return found_open

        if found_resolved is not None:
            return _reopen(client, found_resolved)

        return _construct_new(client)


def _scan_breached_incidents(client: httpx.Client) -> tuple[str | None, str | None]:
    """One combined pass over every breached first_response task_sla record, checking each
    referenced Incident's state exactly once.

    Returns:
        (open_match, resolved_match) — `open_match` is an Incident number already satisfying
        Path 1 (breached and not resolved/closed), if any. `resolved_match` is the first
        resolved/closed Incident found with a breached first_response record, kept as a
        candidate for Path 3 (see `_reopen`) so this module never re-fetches the same Incident
        twice across paths.
    """
    resolved_candidate: str | None = None
    page = 1
    scanned = 0
    while scanned < _MAX_SCAN_RECORDS:
        breached = client.get(
            "/sla",
            params={
                "sla_definition": "first_response", "breached": "true",
                "page": page, "page_size": _SCAN_PAGE_SIZE,
            },
        ).json()
        items = breached.get("items", [])
        if not items:
            return None, resolved_candidate
        for record in items:
            number = record["incident_number"]
            incident = client.get(f"/incidents/{number}").json()
            scanned += 1
            if incident["state"] not in ("resolved", "closed"):
                return incident["number"], resolved_candidate
            if resolved_candidate is None:
                resolved_candidate = incident["number"]
        if page * _SCAN_PAGE_SIZE >= breached.get("total", 0):
            return None, resolved_candidate
        page += 1
    return None, resolved_candidate


def _reopen(client: httpx.Client, number: str) -> str:
    """Path 3 (this module's own addition — see module docstring): the seeded fixture's breached
    first_response records all belong to resolved/closed Incidents by design (Principle 6's
    "incidents resolved with an open SLA breach" discrepancy), so Path 1 can never succeed
    against the real itsm-api. Move one such Incident back to `in_progress` via the documented,
    unguarded PATCH endpoint — never touching the database file, never modifying the task_sla
    record itself."""
    reopened = client.patch(f"/incidents/{number}", json={"state": "in_progress"})
    reopened.raise_for_status()
    return reopened.json()["number"]


def _construct_new(client: httpx.Client) -> str:
    """Path 2 (fallback, per the plan's design decision): create a throwaway Incident and poll
    for itsm-api to derive a breached first_response task_sla record live. Kept even though
    empirical testing shows itsm-api's POST /incidents never does this, so a future itsm-api
    revision that adds live derivation is picked up automatically instead of silently skipped."""
    created = client.post(
        "/incidents",
        json={
            "account_id": "ACCOUNT-1001", "category": "network",
            "short_description": "mcp-e2e breached-SLA fixture incident",
            "description": "constructed by tests_e2e/breached_sla_fixture.py per mcp-e2e.spec.md Preconditions",
            "state": "new", "priority": 1,
        },
    )
    created.raise_for_status()
    number = created.json()["number"]

    deadline = time.monotonic() + _POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        records = client.get(
            "/sla", params={"incident_number": number, "sla_definition": "first_response"}
        ).json()
        for record in records.get("items", []):
            if record["has_breached"] is True:
                return number
        time.sleep(_POLL_INTERVAL_SECONDS)

    raise BreachedSlaFixtureUnavailable(
        f"E2E_BREACHED_FIXTURE_UNAVAILABLE: no existing not-yet-resolved Incident with a breached "
        f"first_response task_sla was found, no existing resolved Incident with a breached "
        f"first_response task_sla could be reopened, and Incident {number} (created for this "
        f"fixture) never acquired a breached first_response record within "
        f"{_POLL_TIMEOUT_SECONDS}s. This means itsm-api's POST /incidents does not derive "
        f"task_sla records live and no breached fixture row exists at all — see "
        f"mcp-e2e.plan.md's Architecture section and this module's own docstring for the "
        f"residual risk this documents."
    )
