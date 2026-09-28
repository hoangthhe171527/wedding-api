"""Use case: đăng xuất.

Đăng xuất phải **luôn thành công**: client đã xoá token cục bộ trước khi nghe câu
trả lời, nên trả lỗi chỉ làm người dùng hoang mang mà không sửa được gì.
"""

from __future__ import annotations

from app.core.base_model import utc_now
from app.core.context import ActorContext
from app.core.logging import get_logger
from app.core.security.revocation import revoke_session, revoke_user
from app.core.security.tokens import hash_refresh_token
from app.modules.identity.domain.repositories import AuthSessionRepository

log = get_logger(__name__)


class LogoutUser:
    """Thu hồi phiên hiện tại (hoặc mọi phiên)."""

    def __init__(self, sessions: AuthSessionRepository) -> None:
        self._sessions = sessions

    async def execute(
        self, actor: ActorContext, *, refresh_token: str | None = None, all_devices: bool = False
    ) -> int:
        """Thu hồi phiên. Trả số phiên thực sự bị thu hồi."""
        if all_devices:
            revoked = await self._sessions.revoke_all_for_user(actor.user_id)
            # Thu hồi trong Mongo mới giết refresh token; access token là JWT tự
            # chứng minh nên phải chặn thêm ở Redis.
            await revoke_user(actor.user_id, at=utc_now())
            log.info("logout_all", user_id=str(actor.user_id), revoked_sessions=revoked)
            return revoked

        revoked = 0
        if actor.session_id is not None and await self._sessions.revoke(
            actor.tenant_id, actor.session_id
        ):
            await revoke_session(actor.session_id)
            revoked += 1

        if refresh_token:
            session = await self._sessions.find_by_refresh_hash(hash_refresh_token(refresh_token))
            # Token của người khác: im lặng bỏ qua, không biến /logout thành công
            # cụ dò xem một chuỗi token có thật hay không.
            if (
                session is not None
                and session.user_id == actor.user_id
                and not session.is_revoked
                and session.id != actor.session_id
            ):
                await self._sessions.revoke(session.tenant_id, session.id)
                await revoke_session(session.id)
                revoked += 1

        log.info("logout", user_id=str(actor.user_id), revoked_sessions=revoked)
        return revoked


__all__ = ["LogoutUser"]
