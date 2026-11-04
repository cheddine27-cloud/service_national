"""FastAPI application factory. Binds conceptually to 127.0.0.1 only (binding
happens in server.py / uvicorn). Swagger UI is served locally at /docs."""

import sqlite3  # needed by exception handlers registered above
import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import db  # noqa: F401 - makes sure the legacy package import path works

from .config import ConfigurationError, load_config
from .routes import meta, optional, reports, squads, students, weeks


def _host_guard(app: FastAPI):
    """Reject any request whose Host header is not localhost - defence in
    depth so the API can never be used from another machine."""

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "testserver"):
            return JSONResponse({"detail": "local use only"}, status_code=403)
        return await call_next(request)


def create_app() -> FastAPI:
    app = FastAPI(
        title="National Service Local API",
        version="1.0.0",
        description="Local-only REST bridge over the existing Python "
                    "business logic (db.py / scheduler.py / reports.py).",
        docs_url="/docs",
        redoc_url=None,
    )
    _host_guard(app)

    app.include_router(meta.router)
    app.include_router(squads.router)
    app.include_router(students.router)
    app.include_router(weeks.router)
    app.include_router(optional.router)
    app.include_router(reports.router)

    @app.exception_handler(FileNotFoundError)
    async def db_missing(request, exc: FileNotFoundError):
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(sqlite3.Error)
    async def sqlite_err(request, exc: sqlite3.Error):
        return JSONResponse({"detail": f"Database error: {exc}"}, status_code=500)

    @app.exception_handler(ConfigurationError)
    async def config_err(request, exc: ConfigurationError):
        return JSONResponse({"detail": str(exc)}, status_code=503)

    return app


app = create_app()
