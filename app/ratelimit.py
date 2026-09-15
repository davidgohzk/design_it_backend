import math
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

from .errors import ApiError

MINUTE = 60.0
DAY = 86_400.0
MAX_TRACKED_CLIENTS = 10_000


class RateLimiter:
    """Sliding-window request limit per client IP, kept in memory (resets on restart)."""

    def __init__(self, per_minute: int, per_day: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.per_minute = max(1, per_minute)
        self.per_day = max(1, per_day)
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def check(self, client_id: str) -> None:
        now = self._clock()
        if len(self._hits) > MAX_TRACKED_CLIENTS:
            self._forget_idle(now)

        hits = self._hits.setdefault(client_id, deque())
        while hits and now - hits[0] >= DAY:
            hits.popleft()
        if len(hits) >= self.per_day:
            self._reject(DAY - (now - hits[0]))

        in_last_minute = 0
        for hit in reversed(hits):
            if now - hit >= MINUTE or in_last_minute >= self.per_minute:
                break
            in_last_minute += 1
        if in_last_minute >= self.per_minute:
            self._reject(MINUTE - (now - hits[-self.per_minute]))

        hits.append(now)

    def _forget_idle(self, now: float) -> None:
        self._hits = {key: hits for key, hits in self._hits.items() if hits and now - hits[-1] < DAY}

    @staticmethod
    def _reject(retry_after: float) -> None:
        raise ApiError(
            429,
            "rate_limited",
            "Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


def rate_limited(request: Request) -> None:
    client_id = request.client.host if request.client else "unknown"
    request.app.state.rate_limiter.check(client_id)
