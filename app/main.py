# Charter-wide foundation file (see plan header). This task mounts only the incidents router;
# each sibling plan's own task adds `app.include_router(...)` for its own router here, in its own
# task, extending this file rather than recreating it.
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db import create_schema, get_connection
from app.errors import http_exception_handler, validation_exception_handler


def create_app(db_path: str) -> FastAPI:
    app = FastAPI(title="mock-servicenow itsm-api")
    conn = get_connection(db_path)
    create_schema(conn)
    app.state.db_conn = conn

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.get("/")
    def health():
        # Not part of this spec's own BEH list, but required charter-wide infrastructure:
        # api-e2e.plan.md's `start_itsm_api()` fixture polls this route to detect a healthy
        # process startup, and mirrors mock-jira's equivalent health route.
        return {"status": "ok", "service": "mock-servicenow"}

    return app


# `DATABASE_PATH` env var override (default "servicenow.db") is what lets
# api-e2e.plan.md's `start_itsm_api()` fixture launch `uvicorn app.main:app` as a real
# subprocess pointed at an isolated temp-file database per e2e run, since a subprocess
# can't be handed a `db_path` argument directly the way `create_app()`'s tests can.
app = create_app(os.environ.get("DATABASE_PATH", "servicenow.db"))
