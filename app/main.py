import time

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings
from .errors import ApiError, error_body
from .llm import UpstreamSlots, create_client
from .ratelimit import RateLimiter, rate_limited
from .routes import router

MAX_BODY_BYTES = 512_000


class BodySizeLimit:
    """Rejects POST requests without a Content-Length or with a body over the limit."""

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST":
            length = dict(scope["headers"]).get(b"content-length")
            error = None
            if length is None:
                error = (411, "length_required", "Requests must include a Content-Length header.")
            elif not length.isdigit() or int(length) > self.max_bytes:
                error = (413, "payload_too_large", "The request is too large.")
            if error:
                status, code, message = error
                await JSONResponse(error_body(code, message), status_code=status)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _describe_validation_error(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "The request is invalid."
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    message = first.get("msg", "is invalid")
    return f"{location}: {message}" if location else message


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
        return JSONResponse(error_body("invalid_request", _describe_validation_error(exc)), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            error_body("http_error", str(exc.detail)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.get("/")
    async def root() -> dict:
        return {"service": "design-it-backend", "status": "ok"}

    @app.api_route("/health", methods=["GET", "HEAD"])
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/health/upstream", dependencies=[Depends(rate_limited)])
    async def upstream_health() -> dict:
        """Checks that this host can reach SoCLaaS at all. Any HTTP status proves the network path works."""
        headers = {"Authorization": f"Bearer {settings.soclaas_api_key}"} if settings.soclaas_api_key else {}
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                response = await http.get(f"{settings.soclaas_base_url}/models", headers=headers)
        except httpx.HTTPError:
            return {"reachable": False, "status": None, "latency_ms": round((time.perf_counter() - started) * 1000)}
        return {
            "reachable": True,
            "status": response.status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }

    app.include_router(router)
    return app


app = create_app()
