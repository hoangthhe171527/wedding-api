"""Use case: đổi mật khẩu của chính mình.

Đổi mật khẩu là phản xạ khi nghi tài khoản bị lộ, nên mọi phiên KHÁC bị cắt —
cả refresh token (Mongo) lẫn access token còn hạn (Redis). Phiên đang dùng được
giữ lại để người dùng không bị đá ra ngay trên chính thiết bị họ vừa đổi.
"""

from __future__ import annotations

from app.core.base_model import utc_now
from app.core.context import ActorContext
from app.core.errors import UnauthorizedError, ValidationError
from app.core.logging import get_logger
from app.core.security.password import hash_password_async, verify_password_async
from app.core.security.revocation import revoke_user
from app.modules.identity.domain.errors import IdentityDomainError, SamePasswordError
from app.modules.identity.domain.repositories import AuthSessionRepository, UserRepository
from app.modules.identity.domain.services import check_password_policy

log = get_logger(__name__)


class ChangeOwnPassword:
    """Đổi mật khẩu, cắt mọi phiên trên thiết bị khác."""

    def __init__(self, users: UserRepository, sessions: AuthSessionRepository) -> None:
        self._users = users
        self._sessions = sessions

    async def execute(self, actor: ActorContext, current_password: str, new_password: str) -> None:
        """Raises:
        ValidationError: mật khẩu hiện tại sai, mật khẩu mới yếu hoặc trùng cũ.
        """
        user = await self._users.find_by_id(actor.tenant_id, actor.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(
                "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", code="account_disabled"
            )
        if not await verify_password_async(current_password, user.password_hash):
            message = "Mật khẩu hiện tại không đúng."
            raise ValidationError(
                message, code="wrong_password", errors={"current_password": [message]}
            )
        try:
            check_password_policy(new_password, field="new_password")
            if await verify_password_async(new_password, user.password_hash):
                raise SamePasswordError
        except IdentityDomainError as exc:
            raise ValidationError(
                exc.message, errors={exc.field or "new_password": [exc.message]}
            ) from exc

        new_hash = await hash_password_async(new_password)
        await self._users.set_password_hash(user.tenant_id, user.id, new_hash)
        revoked = await self._sessions.revoke_all_for_user(
            user.id, except_session_id=actor.session_id
        )
        await revoke_user(user.id, at=utc_now(), except_session_id=actor.session_id)
        log.info("password_changed", user_id=str(user.id), revoked_sessions=revoked)


__all__ = ["ChangeOwnPassword"]
