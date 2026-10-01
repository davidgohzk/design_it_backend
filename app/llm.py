import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import openai
from fastapi import Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from .config import Settings
from .errors import ApiError

logger = logging.getLogger("design_it.llm")

STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=10.0)
# A non-streaming completion (an /api/assess step) sends nothing until the whole reply is generated.
COMPLETION_TIMEOUT = httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def create_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        # The SDK refuses an empty key; without a server key, get_llm rejects every request.
        api_key=settings.soclaas_api_key or "missing-server-key",
        base_url=settings.soclaas_base_url,
        timeout=STREAM_TIMEOUT,
        max_retries=1,
    )


@dataclass(frozen=True)
class LLM:
    client: AsyncOpenAI
    model: str


def get_llm(request: Request) -> LLM:
    """The server's client and model; the browser never supplies a key."""
    settings: Settings = request.app.state.settings
    if not settings.soclaas_api_key:
        raise ApiError(503, "no_server_key", "The server has no SoCLaaS API key configured.")
    return LLM(request.app.state.llm_client, settings.soclaas_model)


class UpstreamSlots:
    """Caps concurrent upstream calls. The event loop is single-threaded, so a counter is enough."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.active = 0

    def acquire(self) -> None:
        if self.active >= self.limit:
            raise ApiError(503, "busy", "The server is handling too many AI requests. Please retry in a moment.")
        self.active += 1

    def release(self) -> None:
        self.active = max(0, self.active - 1)


def upstream_error(exc: Exception) -> ApiError:
    """Translate an SDK error without passing upstream text through (it can echo part of the key)."""
    logger.warning("Upstream call failed: %s (status=%s)", type(exc).__name__, getattr(exc, "status_code", None))

    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return ApiError(502, "server_key_rejected", "The server's SoCLaaS key was rejected. Please contact the site owner.")
    if isinstance(exc, openai.RateLimitError):
        retry_after = exc.response.headers.get("retry-after")
        return ApiError(
            429,
            "upstream_rate_limited",
            "The AI service is rate limiting requests. Please wait and retry.",
            headers={"Retry-After": retry_after} if retry_after else None,
        )
    if isinstance(exc, openai.APITimeoutError):
        return ApiError(504, "upstream_timeout", "The AI service took too long to respond. Please retry.")
    if isinstance(exc, openai.APIConnectionError):
        return ApiError(502, "upstream_unreachable", "The server could not reach the AI service.")
    if isinstance(exc, (openai.BadRequestError, openai.UnprocessableEntityError)):
        return ApiError(400, "upstream_bad_request", "The AI service rejected the request. It may be too long.")
    return ApiError(502, "upstream_error", "The AI service returned an error. Please retry.")


def _sse(data: dict, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _completion_events(
    llm: LLM, slots: UpstreamSlots, messages: list[dict], params: dict, done_meta: dict
) -> AsyncIterator[str]:
    slots.acquire()
    stream = None
    try:
        try:
            stream = await llm.client.chat.completions.create(
                model=llm.model, messages=messages, stream=True, **params
            )
        except openai.APIError as exc:
            raise upstream_error(exc) from None

        yield ": connected\n\n"
        try:
            async for chunk in stream:
                part = chunk.choices[0].delta.content if chunk.choices else None
                if part:
                    yield _sse({"delta": part})
            yield _sse(done_meta, "done")
        except openai.APIError as exc:
            error = upstream_error(exc)
            yield _sse({"code": error.code, "message": error.message}, "error")
        except Exception as exc:
            logger.warning("Stream failed: %s", type(exc).__name__)
            yield _sse({"code": "stream_failed", "message": "The AI response was interrupted. Please retry."}, "error")
    finally:
        slots.release()
        if stream is not None:
            await stream.close()


async def stream_completion(
    llm: LLM, slots: UpstreamSlots, messages: list[dict], **params
) -> StreamingResponse:
    """Stream deltas as SSE. Errors before the first token become real HTTP statuses.

    The final `done` event carries {model}, so a stored transcript records which model answered.
    """
    done_meta = {"model": llm.model}
    events = _completion_events(llm, slots, messages, params, done_meta)
    # Opening the upstream stream here means auth/rate-limit failures raise before headers are sent,
    # and the generator is already started, so it is always finalised (slot released, stream closed).
    first = await anext(events)

    async def body() -> AsyncIterator[str]:
        yield first
        async for event in events:
            yield event

    return StreamingResponse(body(), media_type="text/event-stream", headers=SSE_HEADERS)


async def complete(llm: LLM, slots: UpstreamSlots, messages: list[dict], **params) -> str:
    slots.acquire()
    try:
        completion = await llm.client.chat.completions.create(
            model=llm.model, messages=messages, timeout=COMPLETION_TIMEOUT, **params
        )
    except openai.APIError as exc:
        raise upstream_error(exc) from None
    finally:
        slots.release()

    content = completion.choices[0].message.content if completion.choices else None
    if not content:
        raise ApiError(502, "empty_completion", "The AI returned an empty response. Please retry.")
    return content
