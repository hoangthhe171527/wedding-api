"""Cấu hình structlog (JSON) — ARCHITECTURE §0.6: cấm `print`.

Mọi log đi qua `get_logger(__name__)`. `request_id` được middleware gắn vào
contextvars nên tự xuất hiện trong mọi dòng log của cùng một request.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars
from structlog.processors import CallsiteParameter
from structlog.typing import Processor

from app.core.config import Settings, get_settings

_configured = False


def configure_logging(settings: Settings | None = None) -> None:
    """Cấu hình structlog + logging chuẩn. Idempotent, gọi được nhiều lần."""
    global _configured
    cfg = settings or get_settings()
    level = getattr(logging, cfg.LOG_LEVEL.upper(), logging.INFO)

    shared: list[Processor] = [
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if cfg.LOG_JSON:
        shared.append(
            structlog.processors.CallsiteParameterAdder(
                {CallsiteParameter.MODULE, CallsiteParameter.FUNC_NAME, CallsiteParameter.LINENO}
            )
        )
        renderer: Processor = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # `basicConfig` phải chạy TRƯỚC `structlog.configure`: LoggerFactory của
    # stdlib lấy logger từ hệ thống logging, nên handler phải có sẵn.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)

    structlog.configure(
        processors=[*shared, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        # PHẢI là LoggerFactory của stdlib: `add_logger_name` đọc `logger.name`.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    for noisy in ("uvicorn.access", "uvicorn.error", "asyncio"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

    _configured = True


def get_logger(name: str | None = None) -> Any:
    """Lấy logger. Tự cấu hình nếu chưa (script, test)."""
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
