import asyncio
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Per-process sliding-window limiter.

    NOTE: no Redis by design. Correct for single-process small deployments.
    For multi-process, creation endpoint also enforces DB-backed
    max-pending quota, which is the authoritative abuse guard.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        async with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


limiter = InMemoryRateLimiter()
