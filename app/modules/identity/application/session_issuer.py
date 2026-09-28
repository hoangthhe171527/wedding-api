"""Phát hành phiên đăng nhập — dùng chung cho đăng nhập, đăng ký và xoay vòng token.

Ba đường phải sinh ra token **giống hệt nhau về nội dung**; tách đôi đường code
là cách kinh điển để một bên quên cập nhật rồi sinh lỗ hổng leo thang quyền.
"""

from __future__ import annotations

from app.core.base_model import new_id
from app.core.security.tokens import encode_access_token, generate_refresh_token
from app.modules.identity.application.dtos import ActorProfile, AuthResult
from app.modules.identity.application.ports import PermissionResolver
from app.modules.identity.domain.entities import Studio, User
from app.modules.identity.domain.repositories import AuthSessionRepository


class SessionIssuer:
    """Tạo phiên mới cho một người dùng đã được xác thực."""

    def __init__(self, sessions: AuthSessionRepository, permissions: PermissionResolver) -> None:
        self._sessions = sessions
        self._permissions = permissions

    async def profile_of(self, user: User, studio: Studio) -> ActorProfile:
        """Ảnh chụp actor kèm tập quyền MỚI NHẤT (đọc lại từ `access`, không từ token)."""
        permissions = await self._permissions.execute(tenant_id=studio.id, user_id=user.id)
        return ActorProfile(user=user, studio=studio, permissions=permissions)

    async def issue(
        self,
        user: User,
        studio: Studio,
        *,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> AuthResult:
        """Ghi một phiên mới và trả cặp token kèm hồ sơ actor.

        Khoá chính của phiên trùng `jti` của access token, nên `POST /auth/logout`
        chỉ cần `ActorContext.session_id` là thu hồi đúng phiên đang dùng.
        """
        profile = await self.profile_of(user, studio)
        session_id = new_id()
        access = encode_access_token(
            user_id=user.id,
            tenant_id=studio.id,
            permissions=profile.permissions,
            session_id=session_id,
        )
        refresh = generate_refresh_token()
        await self._sessions.create(
            session_id=session_id,
            tenant_id=studio.id,
            user_id=user.id,
            refresh_token_hash=refresh.hashed,
            expires_at=refresh.expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        return AuthResult(
            access_token=access.token,
            refresh_token=refresh.raw,
            expires_in=access.expires_in,
            expires_at=access.expires_at,
            session_id=session_id,
            profile=profile,
        )


__all__ = ["SessionIssuer"]
