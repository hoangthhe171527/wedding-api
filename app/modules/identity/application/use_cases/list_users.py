"""Use case: danh sách mọi tài khoản cho đội vận hành (`user.manage`).

Xuyên xưởng CÓ CHỦ Ý — đây là màn quản trị hệ thống. Quyền đã được kiểm ở
router; use case chỉ lo ghép dữ liệu: tài khoản + tên xưởng + nhãn vai trò, trong
số truy vấn cố định (không N+1).
"""

from __future__ import annotations

from app.core.pages import Page, PageParams
from app.modules.identity.application.dtos import UserSummary
from app.modules.identity.application.ports import UserRoleReader
from app.modules.identity.domain.repositories import StudioRepository, UserRepository


class ListUsers:
    """Tìm và phân trang mọi tài khoản."""

    def __init__(
        self, users: UserRepository, studios: StudioRepository, roles: UserRoleReader
    ) -> None:
        self._users = users
        self._studios = studios
        self._roles = roles

    async def execute(self, *, query: str | None, params: PageParams) -> Page[UserSummary]:
        page = await self._users.search_all(query=(query or "").strip() or None, params=params)
        user_ids = [user.id for user in page.items]
        studios = {
            studio.id: studio
            for studio in await self._studios.find_many(list({u.tenant_id for u in page.items}))
        }
        labels = await self._roles.labels_for(user_ids)
        return page.map(
            lambda user: UserSummary(
                user=user,
                studio_name=studios[user.tenant_id].name if user.tenant_id in studios else None,
                roles=labels.get(user.id, []),
            )
        )


__all__ = ["ListUsers"]
