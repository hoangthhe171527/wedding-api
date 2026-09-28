"""Cache ngắn hạn trên Redis cho các đường đọc nóng (web thiệp công khai).

Hỏng thì MỞ, như rate limit: Redis chậm / chết thì coi như không có cache và đọc
thẳng DB — không bao giờ để cache làm lỗi một trang khách đang mở.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.core.redis import get_redis, key

log = get_logger(__name__)


async def get_json(*parts: object) -> Any | None:
    try:
        raw = await get_redis().get(key("cache", *parts))
    except Exception as exc:
        log.warning("cache_unavailable", error=str(exc))
        return None
    return json.loads(raw) if raw else None


async def set_json(value: Any, ttl_seconds: int, *parts: object) -> None:
    try:
        await get_redis().set(
            key("cache", *parts), json.dumps(value, default=str, ensure_ascii=False), ex=ttl_seconds
        )
    except Exception as exc:
        log.warning("cache_unavailable", error=str(exc))


async def delete(*parts: object) -> None:
    try:
        await get_redis().delete(key("cache", *parts))
    except Exception as exc:
        log.warning("cache_unavailable", error=str(exc))


__all__ = ["delete", "get_json", "set_json"]
