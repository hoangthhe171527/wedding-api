"""Schema HTTP của `identity`.

Hình dạng `actor` ở đây là thứ web đọc để ẩn/hiện chức năng — đổi nó là đổi hợp
đồng với client, không đổi tuỳ tiện.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.security.tokens import TOKEN_TYPE
from app.modules.identity.application.dtos import ActorProfile, AuthResult, UserSummary
from app.modules.identity.domain.entities import User


class LoginIn(BaseModel):
    """Thân yêu cầu đăng nhập."""

    identifier: str = Field(
        min_length=3,
        max_length=190,
        description="Email hoặc số điện thoại.",
        examples=["admin@thiephy.vn", "0912345678"],
    )
    password: str = Field(min_length=1, max_length=256)


class RegisterIn(BaseModel):
    """Thân yêu cầu đăng ký tài khoản dùng mẫu. Cần email hoặc số điện thoại."""

    full_name: str = Field(min_length=2, max_length=120, examples=["Trần Huy Hoàng"])
    email: str | None = Field(default=None, max_length=190)
    phone: str | None = Field(default=None, max_length=20)
    password: str = Field(
        min_length=8, max_length=256, description="Tối thiểu 8 ký tự, có chữ và số."
    )


class RefreshIn(BaseModel):
    """Thân yêu cầu xoay vòng refresh token."""

    #: Bỏ trống thì đọc cookie HttpOnly `wedding_refresh` (web).
    refresh_token: str = Field(default="", max_length=512)


class LogoutIn(BaseModel):
    """Thân yêu cầu đăng xuất — mọi trường tuỳ chọn."""

    refresh_token: str | None = Field(default=None, max_length=512)
    all_devices: bool = False


class ChangePasswordIn(BaseModel):
    """Thân yêu cầu đổi mật khẩu."""

    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class StudioOut(BaseModel):
    """Xưởng thiệp của actor."""

    id: UUID
    name: str


class UserOut(BaseModel):
    """Người dùng đang đăng nhập."""

    id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None

    @classmethod
    def of(cls, user: User) -> UserOut:
        return cls(id=user.id, full_name=user.full_name, email=user.email, phone=user.phone)


class ActorOut(BaseModel):
    """Hồ sơ actor: người dùng, xưởng và tập quyền."""

    user: UserOut
    studio: StudioOut
    permissions: list[str]

    @classmethod
    def of(cls, profile: ActorProfile) -> ActorOut:
        return cls(
            user=UserOut.of(profile.user),
            studio=StudioOut(id=profile.studio.id, name=profile.studio.name),
            permissions=profile.sorted_permissions,
        )


class TokenOut(BaseModel):
    """Cặp token vừa phát hành kèm hồ sơ actor."""

    access_token: str
    refresh_token: str
    token_type: str = TOKEN_TYPE
    expires_in: int
    expires_at: datetime
    actor: ActorOut

    @classmethod
    def of(cls, result: AuthResult) -> TokenOut:
        return cls(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_in=result.expires_in,
            expires_at=result.expires_at,
            actor=ActorOut.of(result.profile),
        )


class AdminUserOut(BaseModel):
    """Một dòng trong màn quản trị tài khoản."""

    id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    is_active: bool
    studio_id: UUID
    studio_name: str | None = None
    roles: list[str]
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    @classmethod
    def of(cls, item: UserSummary) -> AdminUserOut:
        user = item.user
        return cls(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            is_active=user.is_active,
            studio_id=user.tenant_id,
            studio_name=item.studio_name,
            roles=item.roles,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class SetActiveIn(BaseModel):
    """Khoá / mở khoá tài khoản."""

    is_active: bool


__all__ = [
    "ActorOut",
    "AdminUserOut",
    "ChangePasswordIn",
    "LoginIn",
    "LogoutIn",
    "RefreshIn",
    "RegisterIn",
    "SetActiveIn",
    "TokenOut",
]
