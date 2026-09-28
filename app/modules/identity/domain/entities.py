"""Thực thể thuần của `identity` — không phụ thuộc Beanie/FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Studio:
    """Một Xưởng thiệp — đơn vị tenant của hệ thống.

    Mỗi khách dùng mẫu có một xưởng riêng chứa thông tin cưới, ảnh và khách mời
    của họ. Đội vận hành có một xưởng riêng (không chứa dữ liệu cưới nào) chỉ để
    tài khoản của họ có chỗ đứng trong mô hình tenant.

    Attributes:
        id: Khoá chính; đồng thời là `tenant_id` của mọi bản ghi thuộc xưởng.
        is_active: Xưởng bị khoá thì không ai đăng nhập vào được.
    """

    id: UUID
    name: str
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class User:
    """Người dùng đăng nhập được.

    Email và số điện thoại DUY NHẤT TOÀN HỆ THỐNG: một con người là một tài
    khoản. Phải có ít nhất một trong hai.
    """

    id: UUID
    tenant_id: UUID
    full_name: str
    password_hash: str
    email: str | None = None
    phone: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    last_login_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuthSession:
    """Một phiên đăng nhập, tương ứng đúng một refresh token đang sống.

    Khoá chính của phiên chính là `jti` của access token, nên đăng xuất chỉ cần
    `ActorContext.session_id` là thu hồi được đúng phiên đang dùng.
    """

    id: UUID
    tenant_id: UUID
    user_id: UUID
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
    replaced_by: UUID | None = None
    user_agent: str | None = None
    ip: str | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now


__all__ = ["AuthSession", "Studio", "User"]
