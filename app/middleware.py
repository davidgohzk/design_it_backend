"""Request-level guards that run before any route: body size, and validation-error wording."""

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .errors import error_body

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


def describe_validation_error(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "The request is invalid."
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    message = first.get("msg", "is invalid")
    return f"{location}: {message}" if location else message
