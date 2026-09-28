"""Middleware hạ tầng: mã request và log truy cập có cấu trúc."""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from typing import Final

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.base_model import new_id

REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

log = structlog.get_logger("http")

_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._-]{8,64}")

CallNext = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Gắn `request_id` vào contextvars của structlog và vào header trả về."""

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        # Nhận id của client chỉ khi đúng khuôn (vd id của proxy phía trước); còn lại tự
        # sinh — chuỗi tuỳ ý từ client không được lọt nguyên văn vào log / nhật ký.
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _REQUEST_ID_RE.fullmatch(incoming) else str(new_id())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Một dòng JSON cho mỗi request, kèm thời gian xử lý."""

    SKIP_PATHS: Final[frozenset[str]] = frozenset({"/health", "/health/live"})

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            raise

        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return response


__all__ = ["REQUEST_ID_HEADER", "AccessLogMiddleware", "RequestContextMiddleware"]
