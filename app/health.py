"""Liveness and reachability. Nothing here calls a model for a completion.

/health is what the browser pings on load to wake a sleeping free-tier host, so it must stay cheap
and must not be rate limited. /health/upstream proves this host can reach the provider at all.
"""

import logging
import time

import httpx
from fastapi import APIRouter, Depends, Request

from .ratelimit import rate_limited

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {"service": "design-it-backend", "status": "ok"}


@router.api_route("/health", methods=["GET", "HEAD"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/upstream", dependencies=[Depends(rate_limited)])
async def upstream_health(request: Request) -> dict[str, object]:
    """Checks that this host can reach SoCLaaS at all. Any HTTP status proves the network path works."""
    settings = request.app.state.settings
    headers = {"Authorization": f"Bearer {settings.soclaas_api_key}"} if settings.soclaas_api_key else {}
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(f"{settings.soclaas_base_url}/models", headers=headers)
    except httpx.HTTPError as exc:
        # The one endpoint whose job is diagnosing a network failure, so the reason is logged
        # rather than thrown away. The reply stays shaped the same for the caller.
        logger.warning("Upstream health check failed: %s: %s", type(exc).__name__, exc)
        return {"reachable": False, "status": None, "latency_ms": round((time.perf_counter() - started) * 1000)}
    return {
        "reachable": True,
        "status": response.status_code,
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }
