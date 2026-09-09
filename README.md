# mock-servicenow

A standalone mock of a ServiceNow-shaped ITSM API — incidents, requests, support tickets — for
the adev course tracks to consume as an external system dependency.

Independent repo: no dependency on `course-shared`, the other `mock-*` repos, or any track repo.
Tracks that need it (see `adev-workspace.yaml` at the workspace root for which ones) pull it in
as a service dependency; this repo never depends on them back.

The bundled `agent-ui` (`static/`, served by `itsm-api` at `/`) is skinned as **"DeskNow"** — a
fictional parody brand styled after real enterprise ITSM consoles (dense list/form views, a dark
app navigator, a two-tone wordmark), invented for this training mock and not affiliated with or
endorsed by any real vendor.

## Running with Docker

Bring up the whole stack with one command from the repo root:

```bash
docker compose build   # builds the itsm-api and mcp-server images
docker compose up      # starts itsm-api first, waits for it to be healthy,
                       # then starts mcp-server
```

- `itsm-api` is published at `http://localhost:8030`. Override the host port with `PORT=<port>`.
- `mcp-server` is published at `http://localhost:8031/mcp`, speaking the MCP streamable-http
  transport. Override the host port with `MCP_PORT=<port>`.
- Neither port is exposed beyond `localhost` by default.

Ports across the four mocks do not overlap: the issue tracker uses 8010 and 8011, the CRM 8020
and 8021, this repo 8030 and 8031, and the knowledge base 8040 and 8041. All four can run at
once.

Confirm health with `docker compose ps`, or `curl http://localhost:8030/`.

## Running the UI end-to-end test suite

The agent-ui end-to-end suite drives a real Chromium browser (via Playwright) against a real
`itsm-api` server process. One-time local setup:

```bash
pip install -r requirements-e2e.txt
playwright install chromium
```

Then run it (already covered by the `e2e-smoke` gate, which runs all of `tests_e2e/`):

```bash
python3 -m pytest -q tests_e2e/
```
