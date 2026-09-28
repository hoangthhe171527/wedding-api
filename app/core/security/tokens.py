"""JWT truy cập và refresh token — ARCHITECTURE §1.5.

Access token: JWT HS256, TTL 15 phút, claim `sub`, `tenant_id`, `perms`, `jti`,
`exp`, `iat`, `iss`.

Refresh token: chuỗi ngẫu nhiên 256-bit. DB **chỉ lưu bản băm** (SHA-256 — entropy
đã đủ cao nên không cần KDF chậm), TTL 30 ngày, xoay vòng mỗi lần dùng.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.base_model import new_id
from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError
from app.core.permissions import normalize as normalize_permissions

REFRESH_TOKEN_BYTES: Final[int] = 32  # 256 bit
# Không phải bí mật: đây là giá trị `token_type` của OAuth2 trả cho client.
TOKEN_TYPE: Final[str] = "Bearer"  # noqa: S105


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Nội dung đã giải mã và xác thực của access token."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    permissions: frozenset[str]
    session_id: uuid.UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    """Access token vừa phát hành cùng thông tin hết hạn."""

    token: str
    expires_in: int
    expires_at: datetime
    session_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    """Refresh token vừa phát hành. `raw` trả cho client **một lần**; DB lưu `hashed`."""

    raw: str
    hashed: str
    expires_at: datetime


def _uuid_or_none(value: object) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def encode_access_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    permissions: frozenset[str] | set[str] | list[str],
    session_id: uuid.UUID | None = None,
    settings: Settings | None = None,
) -> IssuedAccessToken:
    """Phát hành access token cho một người dùng."""
    cfg = settings or get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=cfg.ACCESS_TTL_MIN)
    jti = session_id or new_id()

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "perms": sorted(permissions),
        "jti": str(jti),
        "iss": cfg.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, cfg.JWT_SECRET, algorithm=cfg.JWT_ALG)
    return IssuedAccessToken(
        token=token,
        expires_in=cfg.ACCESS_TTL_MIN * 60,
        expires_at=expires_at,
        session_id=jti,
    )


def decode_access_token(token: str, *, settings: Settings | None = None) -> AccessTokenClaims:
    """Giải mã và xác thực access token.

    Raises:
        UnauthorizedError: token hỏng, sai chữ ký, sai issuer hoặc đã hết hạn.
    """
    cfg = settings or get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            cfg.JWT_SECRET,
            algorithms=[cfg.JWT_ALG],
            issuer=cfg.JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", code="token_expired"
        ) from exc
    except InvalidTokenError as exc:
        raise UnauthorizedError(
            "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", code="token_invalid"
        ) from exc

    user_id = _uuid_or_none(payload.get("sub"))
    tenant_id = _uuid_or_none(payload.get("tenant_id"))
    session_id = _uuid_or_none(payload.get("jti"))
    if user_id is None or tenant_id is None or session_id is None:
        raise UnauthorizedError(
            "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", code="token_invalid"
        )

    return AccessTokenClaims(
        user_id=user_id,
        tenant_id=tenant_id,
        # Token mang `perms` đã lọc qua catalog: slug lạ/đã bỏ không cấp được gì.
        permissions=normalize_permissions(payload.get("perms")),
        session_id=session_id,
        issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=UTC),
        expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
    )


def hash_refresh_token(raw: str) -> str:
    """Băm refresh token để lưu DB. Luôn dùng hàm này, không lưu bản thô."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_refresh_token(raw: str, hashed: str) -> bool:
    """So khớp refresh token thô với bản băm, chống tấn công đo thời gian."""
    return hmac.compare_digest(hash_refresh_token(raw), hashed)


def generate_refresh_token(*, settings: Settings | None = None) -> IssuedRefreshToken:
    """Sinh refresh token mới (256 bit) kèm hạn dùng."""
    cfg = settings or get_settings()
    raw = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    return IssuedRefreshToken(
        raw=raw,
        hashed=hash_refresh_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=cfg.REFRESH_TTL_DAYS),
    )


__all__ = [
    "REFRESH_TOKEN_BYTES",
    "TOKEN_TYPE",
    "AccessTokenClaims",
    "IssuedAccessToken",
    "IssuedRefreshToken",
    "decode_access_token",
    "encode_access_token",
    "generate_refresh_token",
    "hash_refresh_token",
    "verify_refresh_token",
]
