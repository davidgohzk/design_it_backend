"""The app factory: settings, shared state, middleware, error shape, routes.

One feature per router — chat, assess — each owning its own prompts, schemas and route, so
a change to one AI call touches one package. Everything they share (the model client, the rate
limiter, the error shape) lives at this level.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .assess.routes import router as assess_router
from .chat.routes import router as chat_router
from .config import Settings
from .errors import ApiError, error_body
from .health import router as health_router
from .llm import UpstreamSlots, create_client
from .middleware import MAX_BODY_BYTES, BodySizeLimit, describe_validation_error
from .ratelimit import RateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="Design_IT backend",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )
    app.state.settings = settings
    app.state.llm_client = create_client(settings)
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_per_day)
    app.state.upstream_slots = UpstreamSlots(settings.max_concurrent_upstream)

    # The last middleware added is outermost, so CORS headers are also set on 411/413 responses.
    app.add_middleware(BodySizeLimit, max_bytes=MAX_BODY_BYTES)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Retry-After"],
        max_age=600,
    )

    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.message), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(error_body("invalid_request", describe_validation_error(exc)), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            error_body("http_error", str(exc.detail)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(assess_router)
    return app


app = create_app()
