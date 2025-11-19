from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict

from .config import settings


@dataclass(slots=True)
class RateLimitResult:
    """Outcome of a rate-limit check."""

    allowed: bool
    retry_after_seconds: int | None = None


class SimpleRateLimiter:
    """In-memory sliding-window rate limiter keyed by an identifier (e.g., IP)."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> RateLimitResult:
        """Return whether another request is allowed for the given key."""
        if self._max_requests <= 0:
            return RateLimitResult(allowed=True)

        now = time.monotonic()
        async with self._lock:
            bucket = self._hits.setdefault(key, deque())
            cutoff = now - self._window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self._max_requests:
                retry_after = self._compute_retry_after(bucket[0], now)
                return RateLimitResult(allowed=False, retry_after_seconds=retry_after)

            bucket.append(now)
            return RateLimitResult(allowed=True)

    def _compute_retry_after(self, oldest_timestamp: float, now: float) -> int:
        remaining = (oldest_timestamp + self._window_seconds) - now
        return max(1, int(math.ceil(remaining)))


_public_run_rate_limiter: SimpleRateLimiter | None = None


def get_public_run_rate_limiter() -> SimpleRateLimiter:
    """Singleton limiter for anonymous public fact-check runs."""
    global _public_run_rate_limiter
    if _public_run_rate_limiter is None:
        _public_run_rate_limiter = SimpleRateLimiter(
            max_requests=settings.public_run_rate_limit_requests,
            window_seconds=settings.public_run_rate_limit_window_seconds,
        )
    return _public_run_rate_limiter


def reset_public_run_rate_limiter() -> None:
    """Helper for tests to rebuild the limiter with current settings."""
    global _public_run_rate_limiter
    _public_run_rate_limiter = None
