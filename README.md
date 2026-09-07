# mock-servicenow

A standalone mock of a ServiceNow-shaped ITSM API — incidents, requests, support tickets — for
the adev course tracks to consume as an external system dependency.

Independent repo: no dependency on `course-shared`, the other `mock-*` repos, or any track repo.
Tracks that need it (see `adev-workspace.yaml` at the workspace root for which ones) pull it in
as a service dependency; this repo never depends on them back.

Not yet scoped. Run `/adev:brainstorm` here to charter what the mock API surface needs to cover
before implementing it.

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
