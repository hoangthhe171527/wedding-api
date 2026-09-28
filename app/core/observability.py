"""Báo lỗi và hiệu năng về Sentry — TUỲ CHỌN: không có `SENTRY_DSN` thì không làm gì.

Mỗi sự kiện gắn `request_id` (trùng header `X-Request-ID` và log JSON) để đối chiếu
khi khách báo lỗi. Không gửi dữ liệu cá nhân mặc định (`send_default_pii=False`):
thân yêu cầu có tên khách mời, số điện thoại.
"""

from __future__ import annotations

from typing import Any

import sentry_sdk
import structlog

from app.core.config import Settings


def _attach_request_id(event: Any, _hint: Any) -> Any:
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    if request_id:
        event.setdefault("tags", {})["request_id"] = request_id
    return event


def init_observability(cfg: Settings) -> bool:
    """Bật Sentry nếu có DSN. Trả True nếu đã bật."""
    if not cfg.SENTRY_DSN:
        return False
    sentry_sdk.init(
        dsn=cfg.SENTRY_DSN,
        environment=str(cfg.ENV),
        release=cfg.APP_RELEASE or None,
        traces_sample_rate=cfg.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        before_send=_attach_request_id,
    )
    return True


__all__ = ["init_observability"]
