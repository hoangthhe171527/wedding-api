"""Use case xoá tài khoản do chính người dùng yêu cầu.

Apple yêu cầu thao tác này phải bắt đầu được ngay trong app. Xác nhận mật khẩu
giúp tránh việc một người cầm nhầm máy xoá tài khoản đang đăng nhập.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.audit import AuditEventDocument
from app.core.base_model import utc_now
from app.core.context import ActorContext
from app.core.errors import UnauthorizedError, ValidationError
from app.core.logging import get_logger
from app.core.security.password import verify_password_async
from app.core.security.revocation import revoke_user
from app.modules.identity.application.ports import TenantDataDeleter
from app.modules.identity.domain.repositories import (
    AuthSessionRepository,
    StudioRepository,
    UserRepository,
)

log = get_logger(__name__)


class DeleteOwnAccount:
    """Xác nhận mật khẩu rồi xoá toàn bộ dữ liệu của xưởng."""

    def __init__(
        self,
        users: UserRepository,
        studios: StudioRepository,
        sessions: AuthSessionRepository,
        tenant_data: Sequence[TenantDataDeleter],
    ) -> None:
        self._users = users
        self._studios = studios
        self._sessions = sessions
        self._tenant_data = tuple(tenant_data)

    async def execute(self, actor: ActorContext, password: str) -> None:
        user = await self._users.find_by_id(actor.tenant_id, actor.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(
                "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.",
                code="account_disabled",
            )
        if not await verify_password_async(password, user.password_hash):
            raise ValidationError(
                "Mật khẩu hiện tại không đúng.",
                code="wrong_password",
                errors={"password": ["Mật khẩu hiện tại không đúng."]},
            )

        # Dọn dữ liệu module trước, rồi mới xoá user/studio để lần thử lại vẫn
        # còn một actor hợp lệ nếu kho object hoặc Mongo tạm thời lỗi.
        for deleter in self._tenant_data:
            await deleter.execute(actor.tenant_id)
        await self._sessions.delete_for_tenant(actor.tenant_id)
        await self._users.delete_for_tenant(actor.tenant_id)
        await self._studios.delete(actor.tenant_id)
        await AuditEventDocument.get_motor_collection().delete_many(
            {"$or": [{"tenant_id": actor.tenant_id}, {"actor_id": actor.user_id}]}
        )
        await revoke_user(actor.user_id, at=utc_now())
        log.info(
            "account_deleted",
            user_id=str(actor.user_id),
            tenant_id=str(actor.tenant_id),
        )


__all__ = ["DeleteOwnAccount"]
