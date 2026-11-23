"""Use case: quên mật khẩu và đặt lại mật khẩu dùng một lần.

Ba luồng chính:

1. `RequestPasswordReset`: người dùng tự yêu cầu gửi liên kết đặt lại mật khẩu
   qua email. Nếu tài khoản không tồn tại, bị khoá hoặc chỉ có số điện thoại,
   use case vẫn trả thành công im lặng để không làm lộ danh sách tài khoản.
2. `ResetPassword`: xác thực chính sách mật khẩu mới TRƯỚC khi tiêu thụ token,
   sau đó đánh dấu token đã dùng nguyên tử và thu hồi toàn bộ phiên đăng nhập.
3. `CreateAdminResetLink`: đội vận hành (`user.manage`) tạo liên kết đặt lại
   mật khẩu gửi trực tiếp cho khách dùng số điện thoại (Zalo) hoặc cần hỗ trợ.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.core import audit
from app.core.base_model import utc_now
from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.security.password import hash_password_async
from app.core.security.revocation import revoke_user
from app.modules.identity.application.ports import PasswordResetMailer
from app.modules.identity.domain.enums import IdentifierKind
from app.modules.identity.domain.errors import IdentityDomainError, InvalidIdentifierError
from app.modules.identity.domain.repositories import (
    AuthSessionRepository,
    PasswordResetTokenRepository,
    UserRepository,
)
from app.modules.identity.domain.services import check_password_policy, normalize_identifier

log = get_logger(__name__)

_TOKEN_BYTES = 32


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_reset_token() -> tuple[str, str]:
    """Sinh cặp `(token_thô_gửi_người_dùng, bản_băm_sha256_lưu_DB)`."""
    raw = secrets.token_urlsafe(_TOKEN_BYTES)
    return raw, _hash_reset_token(raw)


@dataclass(frozen=True, slots=True)
class AdminResetLink:
    """Liên kết đặt lại mật khẩu dùng một lần do đội vận hành tạo."""

    reset_url: str
    expires_at: datetime


class RequestPasswordReset:
    """Tạo token đặt lại mật khẩu và gửi email (chống dò tài khoản)."""

    def __init__(
        self,
        users: UserRepository,
        reset_tokens: PasswordResetTokenRepository,
        mailer: PasswordResetMailer,
    ) -> None:
        self._users = users
        self._reset_tokens = reset_tokens
        self._mailer = mailer

    async def execute(self, identifier: str) -> None:
        try:
            kind, normalized = normalize_identifier(identifier)
        except InvalidIdentifierError:
            return
        user = (
            await self._users.find_by_identifier(email=normalized)
            if kind is IdentifierKind.EMAIL
            else await self._users.find_by_identifier(phone=normalized)
        )
        if user is None or not user.is_active or not user.email:
            return

        now = utc_now()
        ttl = get_settings().PASSWORD_RESET_TTL_MINUTES
        expires_at = now + timedelta(minutes=ttl)
        await self._reset_tokens.invalidate_for_user(user.id, now)
        raw, hashed = generate_reset_token()
        await self._reset_tokens.create(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hashed,
            expires_at=expires_at,
        )
        reset_url = f"{get_settings().PUBLIC_WEB_URL}/reset-password?token={raw}"
        await self._mailer.send_reset_link(
            to_email=user.email,
            full_name=user.full_name,
            reset_url=reset_url,
            ttl_minutes=ttl,
        )


class ResetPassword:
    """Tiêu thụ token hợp lệ, cập nhật mật khẩu mới và cắt toàn bộ phiên cũ."""

    def __init__(
        self,
        users: UserRepository,
        sessions: AuthSessionRepository,
        reset_tokens: PasswordResetTokenRepository,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._reset_tokens = reset_tokens

    async def execute(self, raw_token: str, new_password: str) -> None:
        """Raises: ValidationError (mật khẩu yếu, token hỏng/hết hạn, tài khoản khoá)."""
        try:
            check_password_policy(new_password, field="new_password")
        except IdentityDomainError as exc:
            raise ValidationError(
                exc.message, errors={exc.field or "new_password": [exc.message]}
            ) from exc

        cleaned = raw_token.strip()
        if not cleaned:
            raise ValidationError(
                "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
                code="reset_token_invalid",
            )
        consumed = await self._reset_tokens.consume(_hash_reset_token(cleaned), utc_now())
        if consumed is None:
            raise ValidationError(
                "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
                code="reset_token_invalid",
            )
        user = await self._users.find_by_id(consumed.tenant_id, consumed.user_id)
        if user is None or not user.is_active:
            raise ValidationError("Tài khoản không khả dụng.", code="account_disabled")

        new_hash = await hash_password_async(new_password)
        await self._users.set_password_hash(user.tenant_id, user.id, new_hash)
        revoked = await self._sessions.revoke_all_for_user(user.id)
        await revoke_user(user.id, at=utc_now())
        await audit.record(
            "password.reset",
            actor_id=user.id,
            target_type="user",
            target_id=user.id,
            tenant_id=user.tenant_id,
            details={"via": "admin_link" if consumed.created_by_admin_id else "self_service"},
        )
        log.info("password_reset_completed", user_id=str(user.id), revoked_sessions=revoked)


class CreateAdminResetLink:
    """Đội vận hành cấp liên kết đặt lại mật khẩu dùng một lần cho khách cần hỗ trợ."""

    def __init__(
        self,
        users: UserRepository,
        reset_tokens: PasswordResetTokenRepository,
    ) -> None:
        self._users = users
        self._reset_tokens = reset_tokens

    async def execute(self, actor: ActorContext, user_id: UUID) -> AdminResetLink:
        """Raises: NotFoundError, ConflictError (tài khoản bị khoá)."""
        user = await self._users.find_any_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy tài khoản.", code="user_not_found")
        if not user.is_active:
            raise ConflictError(
                "Tài khoản đang bị khoá. Hãy mở khoá trước khi tạo link đặt lại mật khẩu.",
                code="account_disabled",
            )
        now = utc_now()
        ttl = get_settings().PASSWORD_RESET_TTL_MINUTES
        expires_at = now + timedelta(minutes=ttl)
        await self._reset_tokens.invalidate_for_user(user.id, now)
        raw, hashed = generate_reset_token()
        await self._reset_tokens.create(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hashed,
            expires_at=expires_at,
            created_by_admin_id=actor.user_id,
        )
        reset_url = f"{get_settings().PUBLIC_WEB_URL}/reset-password?token={raw}"
        await audit.record(
            "user.reset_link_created",
            actor_id=actor.user_id,
            target_type="user",
            target_id=user.id,
            tenant_id=user.tenant_id,
            details={"expires_at": expires_at.isoformat()},
        )
        log.info("admin_reset_link_created", user_id=str(user.id), by=str(actor.user_id))
        return AdminResetLink(reset_url=reset_url, expires_at=expires_at)


__all__ = [
    "AdminResetLink",
    "CreateAdminResetLink",
    "RequestPasswordReset",
    "ResetPassword",
    "generate_reset_token",
]
