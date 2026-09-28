"""Use case: xoay vòng refresh token, kèm bẫy phát hiện trộm token.

Một refresh token chỉ dùng đúng một lần. Nếu một token ĐÃ THU HỒI được mang ra
dùng lại, nghĩa là có hai bên cùng giữ nó — bên thật và bên trộm. Không biết bên
nào đang gọi, nên thu hồi TOÀN BỘ phiên của người dùng và bắt đăng nhập lại
("refresh token rotation with reuse detection" — OAuth 2.0 BCP).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.core.base_model import utc_now
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger
from app.core.security.revocation import revoke_user
from app.core.security.tokens import hash_refresh_token
from app.modules.identity.application.dtos import AuthResult, RefreshCommand
from app.modules.identity.application.session_issuer import SessionIssuer
from app.modules.identity.domain.repositories import (
    AuthSessionRepository,
    StudioRepository,
    UserRepository,
)

log = get_logger(__name__)

SESSION_INVALID_MESSAGE = "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại."
SESSION_REUSED_MESSAGE = (
    "Phiên đăng nhập đã bị thu hồi vì phát hiện dấu hiệu bất thường. Vui lòng đăng nhập lại."
)


class RefreshToken:
    """Đổi refresh token cũ lấy cặp token mới."""

    def __init__(
        self,
        sessions: AuthSessionRepository,
        users: UserRepository,
        studios: StudioRepository,
        issuer: SessionIssuer,
    ) -> None:
        self._sessions = sessions
        self._users = users
        self._studios = studios
        self._issuer = issuer

    async def execute(self, command: RefreshCommand) -> AuthResult:
        """Xoay vòng token.

        Raises:
            UnauthorizedError: token không tồn tại, hết hạn, đã bị thu hồi (kèm
                thu hồi toàn bộ phiên), hoặc tài khoản/xưởng đã bị khoá.
        """
        raw = command.refresh_token.strip()
        if not raw:
            raise UnauthorizedError(SESSION_INVALID_MESSAGE, code="refresh_token_invalid")

        # TIÊU THỤ token trước mọi việc khác: một thao tác nguyên tử vừa kiểm
        # "còn sống" vừa đánh dấu "đã dùng". Đọc-kiểm-ghi tách rời để lọt hai
        # request song song cùng qua cửa — một token sinh hai chuỗi phiên sống.
        now = utc_now()
        token_hash = hash_refresh_token(raw)
        session = await self._sessions.consume_refresh_hash(token_hash, now)
        if session is None:
            raise await self._explain_failed_consume(token_hash, now)

        user = await self._users.find_by_id(session.tenant_id, session.user_id)
        if user is None or not user.is_active:
            await self._sessions.revoke_all_for_user(session.user_id)
            await revoke_user(session.user_id, at=now)
            raise UnauthorizedError(SESSION_INVALID_MESSAGE, code="account_disabled")

        studio = await self._studios.find_by_id(session.tenant_id)
        if studio is None or not studio.is_active:
            await self._sessions.revoke_all_for_user(session.user_id)
            raise UnauthorizedError(SESSION_INVALID_MESSAGE, code="studio_disabled")

        result = await self._issuer.issue(
            user,
            studio,
            user_agent=command.user_agent or session.user_agent,
            ip=command.ip or session.ip,
        )
        await self._sessions.revoke(session.tenant_id, session.id, replaced_by=result.session_id)
        log.info(
            "refresh_rotated",
            user_id=str(user.id),
            previous_session_id=str(session.id),
            session_id=str(result.session_id),
        )
        return result

    async def _explain_failed_consume(self, token_hash: str, now: datetime) -> UnauthorizedError:
        """Nói đúng vì sao không tiêu thụ được — chỉ nhánh "đã thu hồi" là tấn công."""
        session = await self._sessions.find_by_refresh_hash(token_hash)
        if session is None:
            return UnauthorizedError(SESSION_INVALID_MESSAGE, code="refresh_token_invalid")
        if session.is_expired(now):
            return UnauthorizedError(
                "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
                code="refresh_token_expired",
            )
        return await self._revoke_everything(session.user_id, session.id)

    async def _revoke_everything(self, user_id: UUID, session_id: UUID) -> UnauthorizedError:
        """Token đã thu hồi bị dùng lại -> cắt sạch mọi phiên, cả access token còn hạn."""
        revoked = await self._sessions.revoke_all_for_user(user_id)
        await revoke_user(user_id, at=utc_now())
        log.warning(
            "refresh_token_reused",
            user_id=str(user_id),
            session_id=str(session_id),
            revoked_sessions=revoked,
        )
        return UnauthorizedError(SESSION_REUSED_MESSAGE, code="refresh_token_reused")


__all__ = ["SESSION_INVALID_MESSAGE", "SESSION_REUSED_MESSAGE", "RefreshToken"]
