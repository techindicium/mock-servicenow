# Charter-wide foundation file (see plan header). Generalized so no sibling plan needs to modify
# this file for its own Literal-typed (enum) or bool-typed query/body fields: the `literal_error`
# branch handles every enum (Incident `state`/`priority`, WorkNote `note_type`, TaskSla
# `sla_definition`); the `bool_parsing`/`bool_type` branch handles every boolean query parameter
# (Incident/Escalation `escalated`/`open_only`, SLA `breached`); `field` is read from `loc[-1]`,
# which resolves correctly whether the error came from a request body field or a query parameter.
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code, content={"message": str(detail), "code": "ERROR"}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    for error in errors:
        if error.get("type") == "json_invalid":
            return JSONResponse(
                status_code=400,
                content={"message": "Request body is not valid JSON", "code": "MALFORMED_JSON"},
            )
    first = errors[0] if errors else {}
    field = str(first.get("loc", ["field"])[-1])
    error_type = first.get("type")
    if error_type == "literal_error":
        allowed = first.get("ctx", {}).get("expected", "")
        return JSONResponse(
            status_code=422,
            content={"message": f"{field} must be one of: {allowed}", "code": "VALIDATION_ERROR"},
        )
    if error_type in ("bool_parsing", "bool_type"):
        return JSONResponse(
            status_code=422,
            content={
                "message": f"{field} must be a valid boolean (true or false)",
                "code": "VALIDATION_ERROR",
            },
        )
    return JSONResponse(
        status_code=422,
        content={"message": f"{field} is required", "code": "VALIDATION_ERROR"},
    )
