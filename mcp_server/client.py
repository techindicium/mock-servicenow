import httpx

from mcp_server.errors import UpstreamError, UpstreamUnreachableError


class ItsmApiClient:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None):
        self._http = httpx.AsyncClient(base_url=base_url, transport=transport)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def list_incidents(
        self,
        account_id: str | None = None,
        state: str | None = None,
        category: str | None = None,
        opened_after: str | None = None,
        opened_before: str | None = None,
        escalated: bool | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict:
        params: dict = {}
        if account_id is not None:
            params["account_id"] = account_id
        if state is not None:
            params["state"] = state
        if category is not None:
            params["category"] = category
        if opened_after is not None:
            params["opened_after"] = opened_after
        if opened_before is not None:
            params["opened_before"] = opened_before
        if escalated is not None:
            params["escalated"] = escalated
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        response = await self._request("GET", "/incidents", params=params)
        return response.json()

    async def get_incident(self, number: str) -> dict:
        response = await self._request("GET", f"/incidents/{number}")
        return response.json()

    async def create_incident(
        self,
        account_id: str,
        category: str,
        short_description: str,
        description: str,
        state: str,
        priority: int,
    ) -> dict:
        payload = {
            "account_id": account_id,
            "category": category,
            "short_description": short_description,
            "description": description,
            "state": state,
            "priority": priority,
        }
        response = await self._request("POST", "/incidents", json=payload)
        return response.json()

    async def update_incident(
        self,
        number: str,
        state: str | None = None,
        priority: int | None = None,
        assigned_to: str | None = None,
        assignment_group: str | None = None,
    ) -> dict:
        payload = {}
        if state is not None:
            payload["state"] = state
        if priority is not None:
            payload["priority"] = priority
        if assigned_to is not None:
            payload["assigned_to"] = assigned_to
        if assignment_group is not None:
            payload["assignment_group"] = assignment_group
        response = await self._request("PATCH", f"/incidents/{number}", json=payload)
        return response.json()

    async def list_work_notes(
        self, incident_number: str, page: int | None = None, page_size: int | None = None
    ) -> list[dict]:
        params: dict = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        response = await self._request(
            "GET", f"/incidents/{incident_number}/work_notes", params=params
        )
        return response.json()

    async def add_work_note(
        self, incident_number: str, created_by: str, note_type: str, body: str
    ) -> dict:
        payload = {"created_by": created_by, "note_type": note_type, "body": body}
        response = await self._request(
            "POST", f"/incidents/{incident_number}/work_notes", json=payload
        )
        return response.json()

    async def list_users(self) -> dict:
        response = await self._request("GET", "/users")
        return response.json()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise UpstreamUnreachableError(
                f"Could not reach itsm-api at {self._http.base_url}: {exc}"
            ) from exc
        if response.status_code >= 400:
            body = response.json()
            message = body.get("message", response.text)
            raise UpstreamError(response.status_code, message)
        return response
