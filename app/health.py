"""Liveness and reachability. Nothing here calls a model for a completion.

/health is what the browser pings on load to wake a sleeping free-tier host, so it must stay cheap
and must not be rate limited. /health/upstream proves this host can reach the provider at all.
"""

import time

import httpx
from fastapi import APIRouter, Depends, Request

from .ratelimit import rate_limited

router = APIRouter()


@router.get("/")
async def root() -> dict:
    return {"service": "design-it-backend", "status": "ok"}


@router.api_route("/health", methods=["GET", "HEAD"])
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/upstream", dependencies=[Depends(rate_limited)])
async def upstream_health(request: Request) -> dict:
    """Checks that this host can reach SoCLaaS at all. Any HTTP status proves the network path works."""
    settings = request.app.state.settings
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
