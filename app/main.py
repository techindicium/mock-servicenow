# Charter-wide foundation file (see plan header). This task mounts only the incidents router;
# each sibling plan's own task adds `app.include_router(...)` for its own router here, in its own
# task, extending this file rather than recreating it.
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db import create_schema, get_connection
from app.errors import http_exception_handler, validation_exception_handler
from app.routers.directory import router as directory_router
from app.routers.escalations import router as escalations_router
from app.routers.incidents import router as incidents_router
from app.routers.sla import router as sla_router
from app.routers.work_notes import router as work_notes_router

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(db_path: str) -> FastAPI:
    app = FastAPI(title="mock-servicenow itsm-api")
    conn = get_connection(db_path)
    create_schema(conn)
    app.state.db_conn = conn

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(incidents_router)
    app.include_router(work_notes_router)
    app.include_router(sla_router)
    app.include_router(directory_router)
    app.include_router(escalations_router)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_incident_console() -> FileResponse:
        # Repurposed from a JSON health body ({"status": "ok", ...}) to the agent-ui shell, per
        # incident-console.plan.md's Design decision: PRD.md and the agent-ui charter require
        # the UI at "/", and tests_e2e/servers.py's start_itsm_api() fixture polls this route for
        # a 200 status only — never the JSON body — so this change keeps that poll working
        # unchanged. `include_in_schema=False` keeps this out of the OpenAPI schema, matching
        # the prior health route's intent.
        return FileResponse(str(STATIC_DIR / "index.html"))

    return app


# `DATABASE_PATH` env var override (default "servicenow.db") is what lets
# api-e2e.plan.md's `start_itsm_api()` fixture launch `uvicorn app.main:app` as a real
# subprocess pointed at an isolated temp-file database per e2e run, since a subprocess
# can't be handed a `db_path` argument directly the way `create_app()`'s tests can.
app = create_app(os.environ.get("DATABASE_PATH", "servicenow.db"))
