"""Kết nối Redis dùng chung.

Hệ này không có hàng đợi nền (việc nặng như vẽ thiệp, xuất PDF chạy ở trình
duyệt), nên Redis chỉ gánh hai việc nhỏ: danh sách phiên bị thu hồi và bộ đếm
tần suất. Cả hai đều **hỏng thì mở** — Redis chết không được làm sập đăng nhập.
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_redis: Redis | None = None


def get_redis() -> Redis:
    """Client Redis dùng chung của tiến trình (tự quản pool bên trong)."""
    global _redis
    if _redis is None:
        cfg = get_settings()
        _redis = Redis.from_url(
            cfg.REDIS_URL,
            decode_responses=True,
            # Ngắn: Redis chỉ gánh việc phụ (rate limit, thu hồi phiên, cache) và
            # hỏng thì mở — Redis chậm không được kéo mỗi request thêm cả giây.
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
    return _redis


def key(*parts: object) -> str:
    """Khoá Redis có tiền tố của hệ — tách khỏi dữ liệu của hệ khác trên cùng Redis."""
    return ":".join([get_settings().REDIS_KEY_PREFIX, *(str(part) for part in parts)])


async def redis_healthy() -> bool:
    """Redis có phản hồi hay không — dùng cho `/health`."""
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def close_redis() -> None:
    """Đóng kết nối khi tắt ứng dụng."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None


__all__ = ["close_redis", "get_redis", "key", "redis_healthy"]
