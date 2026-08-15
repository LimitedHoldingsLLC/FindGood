from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware import InMemoryRateLimiter, RequestContextMiddleware
from app.api.routes import admin, admin_auth, deals, health, venues
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, request_id_ctx

settings = get_settings()
configure_logging(settings.log_format, settings.log_level)

app = FastAPI(
    title="FindGood API",
    version="0.1.0",
    description="Consumer marketplace API for genuinely good deals near you.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    InMemoryRateLimiter,
    enabled=settings.rate_limit_enabled and not settings.is_test,
    per_minute=settings.rate_limit_per_minute,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.include_router(health.router)
app.include_router(venues.router)
app.include_router(deals.router)
app.include_router(admin_auth.router)
app.include_router(admin.router)


def _error_payload(code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id_ctx.get(),
        }
    }
    if details:
        body["error"]["details"] = details
    return body


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_payload(exc.code, exc.message, exc.details))


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload("http_error", str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_payload("validation_failed", "Request failed validation"),
    )


@app.exception_handler(Exception)
async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, StarletteHTTPException):
        return await http_error_handler(_request, exc)
    return JSONResponse(
        status_code=500,
        content=_error_payload("internal_error", "An unexpected error occurred"),
    )
