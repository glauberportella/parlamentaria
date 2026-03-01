"""Application middleware — rate limiting, request ID, security headers.

Provides:
- RequestIdMiddleware: generates unique request ID per request, binds to structlog
- SecurityHeadersMiddleware: adds security headers to all responses
- Rate limiter setup via slowapi
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import structlog

from app.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 1. Request ID Middleware
# ---------------------------------------------------------------------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Generate a unique request ID, bind to structlog, measure response time.

    Adds headers:
    - X-Request-Id: unique UUID per request
    - X-Response-Time: processing time in milliseconds
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Bind request_id to structlog context for all downstream logs
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
        )

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

        logger.info(
            "http.request",
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        return response


# ---------------------------------------------------------------------------
# 2. Security Headers Middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related headers to every response.

    Headers set:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restricted camera/microphone/geolocation
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


# ---------------------------------------------------------------------------
# 3. Rate Limiter (slowapi)
# ---------------------------------------------------------------------------

from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_rate_limit_key(request: Request) -> str:
    """Extract rate limit key: chat_id from JSON body for webhooks, IP otherwise."""
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=["200/minute"],
    storage_uri="memory://",  # In-memory for dev; use Redis URI in production
)
