"""Chữ ký HMAC cho URL tài nguyên công khai (ảnh cưới).

Thẻ `<img src>` không gửi được header `Authorization`, nên ảnh không thể đi qua
bearer token. Thay vào đó mỗi URL mang `exp` + `sig = HMAC(secret, kind:id:exp)`:
chỉ máy chủ ký được, hết hạn tự chết, và lộ một URL chỉ lộ đúng một tấm ảnh.

Khoá ký suy ra từ `JWT_SECRET` qua một nhãn riêng (`media-url:`), để chữ ký URL
và chữ ký token không bao giờ đổi lẫn cho nhau được.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Final

from app.core.config import get_settings

_LABEL: Final[bytes] = b"media-url:"


def _key() -> bytes:
    return hashlib.sha256(_LABEL + get_settings().JWT_SECRET.encode("utf-8")).digest()


def _payload(kind: str, resource_id: str, expires_at: int) -> bytes:
    return f"{kind}:{resource_id}:{expires_at}".encode()


def sign(
    kind: str, resource_id: str, *, ttl_seconds: int, now: float | None = None
) -> tuple[int, str]:
    """Ký một tài nguyên. Trả `(exp, sig)` để ghép vào query string."""
    expires_at = int(now if now is not None else time.time()) + ttl_seconds
    digest = hmac.new(_key(), _payload(kind, resource_id, expires_at), hashlib.sha256)
    return expires_at, digest.hexdigest()


def verify(kind: str, resource_id: str, *, expires_at: int, signature: str) -> bool:
    """Chữ ký đúng VÀ chưa hết hạn."""
    if expires_at < int(time.time()):
        return False
    expected = hmac.new(_key(), _payload(kind, resource_id, expires_at), hashlib.sha256)
    return hmac.compare_digest(expected.hexdigest(), signature)


__all__ = ["sign", "verify"]
