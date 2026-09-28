"""DTO nội bộ giữa các tầng của `identity` — KHÔNG phải schema HTTP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.identity.domain.entities import Studio, User


@dataclass(frozen=True, slots=True)
class LoginCommand:
    """Yêu cầu đăng nhập (định danh chưa chuẩn hoá)."""

    identifier: str
    password: str
    user_agent: str | None = None
    ip: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterCommand:
    """Khách tự đăng ký tài khoản dùng mẫu."""

    full_name: str
    password: str
    email: str | None = None
    phone: str | None = None
    user_agent: str | None = None
    ip: str | None = None


@dataclass(frozen=True, slots=True)
class RefreshCommand:
    """Yêu cầu xoay vòng refresh token."""

    refresh_token: str
    user_agent: str | None = None
    ip: str | None = None


@dataclass(frozen=True, slots=True)
class ActorProfile:
    """Ảnh chụp đầy đủ về actor hiện tại — dữ liệu cho `GET /auth/me`."""

    user: User
    studio: Studio
    permissions: frozenset[str]

    @property
    def sorted_permissions(self) -> list[str]:
        """Tập quyền đã sắp xếp để phía client so sánh ổn định."""
        return sorted(self.permissions)


@dataclass(frozen=True, slots=True)
class AuthResult:
    """Kết quả của đăng nhập, đăng ký và xoay vòng refresh token."""

    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: datetime
    session_id: UUID
    profile: ActorProfile


@dataclass(frozen=True, slots=True)
class UserSummary:
    """Một dòng trong màn quản trị tài khoản."""

    user: User
    studio_name: str | None
    roles: list[str] = field(default_factory=list)


__all__ = [
    "ActorProfile",
    "AuthResult",
    "LoginCommand",
    "RefreshCommand",
    "RegisterCommand",
    "UserSummary",
]
