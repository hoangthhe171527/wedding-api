"""Danh sách phiên đã bị thu hồi, để access token chết ngay thay vì sau 15 phút.

Access token là JWT tự chứng minh: máy chủ đọc chữ ký rồi tin, không hỏi ai. Thu
hồi một phiên vì thế không làm gì được với token đã phát — cho tới `exp`, nó vẫn
mở được mọi cửa. Ba lúc cần đóng cửa NGAY: đăng xuất, đổi mật khẩu, và phát hiện
refresh token bị dùng lại (đã có kẻ trộm).

Cách vá không phải đọc `auth_sessions` mỗi request (một lượt Mongo trên mọi
đường) mà là danh sách chặn nhỏ trên Redis, sống đúng bằng tuổi thọ access token.

Hai hình dạng khoá:

* `revoked:s:<session_id>` — thu hồi ĐÚNG một phiên.
* `revoked:u:<user_id>` — thu hồi TẤT CẢ, lưu mốc thời gian; token phát trước
  mốc đều chết. `revoked:u:<user_id>:except` tha đúng một phiên (người đổi mật
  khẩu trên máy này thì máy khác bị đá ra, còn máy đang cầm thì không).

**Hỏng thì mở, không đóng.** Redis chết mà chọn đóng là đá toàn bộ người dùng ra
vì một thành phần phụ trợ trục trặc.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis, key

log = get_logger(__name__)

#: Dư ra sau `exp` để hở đồng hồ giữa các nút không thành một khe lọt.
_SKEW_SECONDS: Final[int] = 60


def _session_key(session_id: uuid.UUID) -> str:
    return key("revoked", "s", session_id)


def _user_key(user_id: uuid.UUID) -> str:
    return key("revoked", "u", user_id)


def _except_key(user_id: uuid.UUID) -> str:
    return key("revoked", "u", user_id, "except")


def _ttl_seconds(settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return cfg.ACCESS_TTL_MIN * 60 + _SKEW_SECONDS


async def revoke_session(session_id: uuid.UUID) -> None:
    """Chặn access token của đúng một phiên."""
    try:
        await get_redis().set(_session_key(session_id), "1", ex=_ttl_seconds())
    except Exception:
        # Không ném: phiên đã bị thu hồi trong Mongo, phần này chỉ rút ngắn quãng
        # token còn sống. Làm hỏng cả thao tác đăng xuất vì Redis thì tệ hơn.
        log.warning("revocation_write_failed", session_id=str(session_id))


async def revoke_user(
    user_id: uuid.UUID, *, at: datetime, except_session_id: uuid.UUID | None = None
) -> None:
    """Chặn mọi access token của một người dùng phát trước mốc `at`."""
    ttl = _ttl_seconds()
    try:
        redis = get_redis()
        await redis.set(_user_key(user_id), str(int(at.timestamp())), ex=ttl)
        if except_session_id is None:
            # Giữ lại mốc tha của lần trước là tha nhầm một phiên cũ lần này.
            await redis.delete(_except_key(user_id))
        else:
            await redis.set(_except_key(user_id), str(except_session_id), ex=ttl)
    except Exception:
        log.warning("revocation_write_failed", user_id=str(user_id))


async def is_revoked(*, user_id: uuid.UUID, session_id: uuid.UUID, issued_at: datetime) -> bool:
    """Token này có thuộc một phiên đã bị thu hồi không. Một lượt `MGET` duy nhất."""
    try:
        session_flag, user_cutoff, spared = await get_redis().mget(
            _session_key(session_id), _user_key(user_id), _except_key(user_id)
        )
    except Exception:
        log.warning("revocation_read_failed", session_id=str(session_id))
        return False

    if session_flag is not None:
        return True
    if user_cutoff is None:
        return False
    if spared is not None and str(spared) == str(session_id):
        return False
    try:
        cutoff = int(user_cutoff)
    except (TypeError, ValueError):
        log.warning("revocation_cutoff_unreadable", user_id=str(user_id))
        return False
    # `<=`: token phát đúng giây thu hồi vẫn phải chết (cả hai mốc làm tròn giây).
    return int(issued_at.timestamp()) <= cutoff


__all__ = ["is_revoked", "revoke_session", "revoke_user"]
