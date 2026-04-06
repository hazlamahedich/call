"""Rate limiting middleware for API endpoints.

Uses sliding window counter to enforce rate limits per tenant.
Prevents abuse of expensive operations like TTS sample generation.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding window rate limiter.

    Tracks request counts per tenant within a time window.
    Uses in-memory storage (consider Redis for distributed systems).
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Structure: {org_id: [(timestamp1, count1), (timestamp2, count2), ...]}
        self.requests: Dict[str, list[Tuple[float, int]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, org_id: str) -> bool:
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            org_requests = self.requests[org_id]

            org_requests[:] = [
                (timestamp, count)
                for timestamp, count in org_requests
                if timestamp > window_start
            ]

            total_requests = sum(count for _, count in org_requests)

            if total_requests >= self.max_requests:
                logger.warning(
                    f"Rate limit exceeded for org {org_id}",
                    extra={
                        "code": "RATE_LIMIT_EXCEEDED",
                        "org_id": org_id,
                        "requests": total_requests,
                        "limit": self.max_requests,
                    },
                )
                return False

            if org_requests and org_requests[-1][0] == now:
                org_requests[-1] = (org_requests[-1][0], org_requests[-1][1] + 1)
            else:
                org_requests.append((now, 1))

            if len(self.requests) > 1000:
                idle_orgs = [
                    oid
                    for oid, reqs in self.requests.items()
                    if not reqs or reqs[-1][0] < window_start
                ]
                for oid in idle_orgs:
                    del self.requests[oid]

            return True

    async def get_remaining_requests(self, org_id: str) -> int:
        """Get remaining requests for org in current window.

        Args:
            org_id: Organization ID to check

        Returns:
            Number of remaining requests
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            org_requests = self.requests.get(org_id, [])
            org_requests[:] = [
                (timestamp, count)
                for timestamp, count in org_requests
                if timestamp > window_start
            ]

            total_requests = sum(count for _, count in org_requests)
            return max(0, self.max_requests - total_requests)


# Global rate limiter instances
# Preset sample generation: 10 requests per minute per tenant
preset_sample_limiter = RateLimiter(max_requests=10, window_seconds=60)
knowledge_upload_limiter = RateLimiter(max_requests=20, window_seconds=60)
namespace_audit_limiter = RateLimiter(max_requests=1, window_seconds=300)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on specific endpoints.

    Apply this middleware to endpoints that need rate limiting.
    """

    def __init__(self, app, rate_limiter: RateLimiter, endpoint_path: str):
        """Initialize rate limit middleware.

        Args:
            app: ASGI application
            rate_limiter: RateLimiter instance
            endpoint_path: Path to match for rate limiting
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.endpoint_path = endpoint_path

    async def dispatch(self, request: Request, call_next):
        """Process request and enforce rate limit.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response or raises HTTPException if rate limited
        """
        # Only rate limit specific endpoint
        if not request.url.path.startswith(self.endpoint_path):
            return await call_next(request)

        # Get org_id from JWT token (attached by auth middleware)
        org_id = getattr(request.state, "org_id", None)

        if not org_id:
            # No org_id means request will fail auth anyway
            return await call_next(request)

        # Check rate limit
        allowed = await self.rate_limiter.check_rate_limit(org_id)

        if not allowed:
            remaining = await self.rate_limiter.get_remaining_requests(org_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Please try again later.",
                    "retry_after": self.rate_limiter.window_seconds,
                    "remaining": 0,
                },
                headers={
                    "Retry-After": str(self.rate_limiter.window_seconds),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)
        remaining = await self.rate_limiter.get_remaining_requests(org_id)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
