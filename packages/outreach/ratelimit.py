"""Process-local outbound request limiter for source and CRM adapters."""

from __future__ import annotations

import threading
import time


class RateLimitExceeded(RuntimeError):
    pass


class OutboundRateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        if not isinstance(requests_per_minute, int) or requests_per_minute < 1:
            raise ValueError("requests_per_minute must be a positive integer")
        self.interval = 60.0 / requests_per_minute
        self._next_allowed: dict[str, float] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            next_allowed = self._next_allowed.get(key, 0.0)
            if now < next_allowed:
                raise RateLimitExceeded(f"outbound rate limit exceeded for {key}")
            self._next_allowed[key] = now + self.interval
