"""Use case: khoá / mở khoá một tài khoản (`user.manage`).

Khoá tài khoản cắt MỌI phiên ngay — refresh token lẫn access token còn hạn. Không
cho tự khoá chính mình: đội vận hành khoá nhầm tài khoản của mình là không còn ai
mở lại được qua giao diện.
"""

from __future__ import annotations

from uuid import UUID

from app.core import audit
from app.core.base_model import utc_now
from app.core.context import ActorContext
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.security.revocation import revoke_user
from app.modules.identity.domain.entities import User
from app.modules.identity.domain.repositories import AuthSessionRepository, UserRepository

log = get_logger(__name__)


class SetUserActive:
    """Bật/tắt quyền đăng nhập của một tài khoản."""

    def __init__(self, users: UserRepository, sessions: AuthSessionRepository) -> None:
        self._users = users
        self._sessions = sessions

    async def execute(self, actor: ActorContext, user_id: UUID, *, is_active: bool) -> User:
        if user_id == actor.user_id and not is_active:
            raise ValidationError("Không thể tự khoá tài khoản của chính bạn.", code="self_lock")
        user = await self._users.find_any_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy tài khoản.")

        await self._users.set_active(user_id, is_active=is_active, actor_id=actor.user_id)
        if not is_active:
            revoked = await self._sessions.revoke_all_for_user(user_id)
            await revoke_user(user_id, at=utc_now())
            log.info("user_locked", user_id=str(user_id), by=str(actor.user_id), revoked=revoked)
        else:
            log.info("user_unlocked", user_id=str(user_id), by=str(actor.user_id))

        await audit.record(
            "user.unlocked" if is_active else "user.locked",
            actor_id=actor.user_id,
            target_type="user",
            target_id=user_id,
            tenant_id=user.tenant_id,
        )
        updated = await self._users.find_any_by_id(user_id)
        assert updated is not None
        return updated


__all__ = ["SetUserActive"]
