from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from monitor_comunitario.api.routes_admin import router as admin_router
from monitor_comunitario.api.routes_admin_session import router as admin_session_router
from monitor_comunitario.api.routes_hermes import admin_router as admin_hermes_router
from monitor_comunitario.api.routes_member import router as member_router
from monitor_comunitario.api.routes_notifications import admin_router as admin_notifications_router
from monitor_comunitario.api.routes_outage_notices import router as outage_notices_router
from monitor_comunitario.api.routes_users import admin_router as admin_users_router
from monitor_comunitario.api.routes_users import router as users_router
from monitor_comunitario.api.routes_web import STATIC_DIR
from monitor_comunitario.api.routes_web import router as web_router
from monitor_comunitario.core.config import get_settings, validate_runtime_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.diagnostics import ReadinessRead
from monitor_comunitario.services.rate_limit import get_rate_limit_store

settings = get_settings()
SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize local database structures when the API starts."""
    validate_runtime_settings(settings)
    if settings.app_env.lower() == "production":
        store = get_rate_limit_store()
        if store is None:
            raise RuntimeError("production requires Redis rate limiting")
        store.ping()
    init_db()
    yield


app = FastAPI(
    title="Monitor Comunitário Celesc",
    description="Monitor público de desligamentos programados da Celesc com alertas por endereço.",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Frame-Options"] = "DENY"
    return response

app.include_router(web_router)
app.include_router(users_router)
app.include_router(member_router)
app.include_router(outage_notices_router)
app.include_router(admin_router)
app.include_router(admin_session_router)
app.include_router(admin_users_router)
app.include_router(admin_notifications_router)
app.include_router(admin_hermes_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Return a minimal healthcheck for local development and deploy probes."""
    return {
        "status": "ok",
        "environment": settings.app_env,
        "timezone": settings.app_timezone,
    }


@app.get("/ready", response_model=ReadinessRead)
def readiness_check(session: SessionDep) -> ReadinessRead | JSONResponse:
    """Return readiness status by validating database connectivity."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "error"},
        )

    return ReadinessRead(status="ready", database="ok")
