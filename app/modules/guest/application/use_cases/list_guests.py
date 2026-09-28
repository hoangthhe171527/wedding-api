"""Use case: danh sách khách mời của xưởng."""

from __future__ import annotations

from app.core.context import ActorContext
from app.core.pages import Page, PageParams
from app.modules.guest.domain.entities import Guest
from app.modules.guest.domain.repositories import GuestRepository


class ListGuests:
    """Khách của xưởng actor — lọc/tìm/thống kê chạy ở web trên trọn danh sách."""

    def __init__(self, guests: GuestRepository) -> None:
        self._guests = guests

    async def execute(self, actor: ActorContext, params: PageParams) -> Page[Guest]:
        return await self._guests.list_page(actor.tenant_id, params)


__all__ = ["ListGuests"]
