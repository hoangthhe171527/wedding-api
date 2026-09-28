"""Giới hạn tần suất, đếm bằng Redis.

Bộ đếm theo ô thời gian cố định: mỗi khoá ứng với một ô `window`, `INCR` rồi đặt
hạn cho ô đó. Một vòng gọi Redis, đủ chính xác cho việc chống dò mật khẩu.

**Mở khi hỏng có chủ ý.** Redis chết thì cho request đi qua, chỉ ghi cảnh báo —
giới hạn tần suất là lớp phòng thủ *bổ sung*, mật khẩu vẫn băm Argon2.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.core.errors import RateLimitedError
from app.core.logging import get_logger
from app.core.redis import get_redis, key

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    """Kết quả một lần đếm."""

    allowed: bool
    remaining: int
    retry_after: int


def _slot_key(bucket: str, identity: str, window_seconds: int) -> str:
    slot = int(time.time()) // window_seconds
    return key("ratelimit", bucket, identity, slot)


async def hit(bucket: str, identity: str, *, limit: int, window_seconds: int) -> RateLimitResult:
    """Đếm một lần chạm và cho biết có được đi tiếp hay không."""
    if limit <= 0 or window_seconds <= 0:
        return RateLimitResult(allowed=True, remaining=limit, retry_after=0)

    slot_key = _slot_key(bucket, identity, window_seconds)
    try:
        async with get_redis().pipeline(transaction=True) as pipe:
            pipe.incr(slot_key)
            # Đặt hạn mỗi lần: rẻ, và tránh khoá sống mãi nếu EXPIRE trượt lần đầu.
            pipe.expire(slot_key, window_seconds)
            results = await pipe.execute()
        count = int(results[0])
    except Exception:
        log.warning("rate_limit_unavailable", bucket=bucket)
        return RateLimitResult(allowed=True, remaining=limit, retry_after=0)

    if count > limit:
        retry_after = window_seconds - (int(time.time()) % window_seconds)
        return RateLimitResult(allowed=False, remaining=0, retry_after=max(retry_after, 1))
    return RateLimitResult(allowed=True, remaining=max(limit - count, 0), retry_after=0)


async def guard(
    bucket: str,
    identity: str,
    *,
    limit: int,
    window_seconds: int,
    message: str,
    code: str,
) -> None:
    """Đếm một lần chạm và ném `RateLimitedError` (kèm `retry_after`) nếu vượt."""
    result = await hit(bucket, identity, limit=limit, window_seconds=window_seconds)
    if result.allowed:
        return
    raise RateLimitedError(
        message, code=code, context={"bucket": bucket, "retry_after": result.retry_after}
    )


async def reset(bucket: str, identity: str, *, window_seconds: int) -> None:
    """Xoá bộ đếm của ô hiện tại — gọi sau khi đăng nhập thành công.

    Không có bước này thì người gõ nhầm vài lần rồi đăng nhập đúng vẫn bị tính
    vào hạn mức cũ, và có thể bị chặn ngay sau đó.
    """
    try:
        await get_redis().delete(_slot_key(bucket, identity, window_seconds))
    except Exception:
        log.warning("rate_limit_reset_failed", bucket=bucket)


__all__ = ["RateLimitResult", "guard", "hit", "reset"]
