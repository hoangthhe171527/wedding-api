"""Use case: hồ sơ của actor đang đăng nhập (`GET /auth/me`).

Tập quyền được **đọc mới từ `access`**, không lấy từ token: access token sống 15
phút, còn khi quản trị viên đổi quyền thì người dùng phải thấy ngay ở lần mở
màn hình kế tiếp. Đây là nguồn web dùng để ẩn/hiện menu (chỉ là giao diện — máy
chủ vẫn kiểm quyền ở mọi endpoint).
"""

from __future__ import annotations

from app.core.context import ActorContext
from app.core.errors import UnauthorizedError
from app.modules.identity.application.dtos import ActorProfile
from app.modules.identity.application.session_issuer import SessionIssuer
from app.modules.identity.domain.repositories import StudioRepository, UserRepository


class GetCurrentActor:
    """Trả hồ sơ đầy đủ của người dùng hiện tại."""

    def __init__(
        self, users: UserRepository, studios: StudioRepository, issuer: SessionIssuer
    ) -> None:
        self._users = users
        self._studios = studios
        self._issuer = issuer

    async def execute(self, actor: ActorContext) -> ActorProfile:
        """Raises: UnauthorizedError nếu tài khoản/xưởng đã bị khoá dù token còn hạn."""
        user = await self._users.find_by_id(actor.tenant_id, actor.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(
                "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", code="account_disabled"
            )
        studio = await self._studios.find_by_id(actor.tenant_id)
        if studio is None or not studio.is_active:
            raise UnauthorizedError(
                "Xưởng thiệp của bạn đã ngừng hoạt động. Vui lòng liên hệ quản trị viên.",
                code="studio_disabled",
            )
        return await self._issuer.profile_of(user, studio)


__all__ = ["GetCurrentActor"]
