"""Use case: màn giám sát xưởng thiệp của đội vận hành (`studio.oversee`).

Xuyên xưởng CÓ CHỦ Ý. Chỉ trả số liệu tổng quan — tên cặp đôi, ngày cưới, đường
dẫn, số khách — không trả nội dung khách mời hay số tài khoản mừng cưới.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.wedding.application.ports import GuestCounter
from app.modules.wedding.domain.entities import Wedding
from app.modules.wedding.domain.enums import EventKind
from app.modules.wedding.domain.repositories import WeddingRepository


@dataclass(frozen=True, slots=True)
class StudioOverview:
    """Một dòng của màn giám sát."""

    wedding: Wedding
    guest_count: int
    main_date: str


def _main_date(wedding: Wedding) -> str:
    """Ngày tiệc cưới đầu tiên (hoặc sự kiện đầu tiên) — cùng luật `mainEvent()`."""
    events = sorted(wedding.content.events, key=lambda item: (item.date, item.time))
    for event in events:
        if event.kind is EventKind.TIEC and event.date:
            return event.date
    return next((event.date for event in events if event.date), "")


class ListStudios:
    """Mọi đám cưới kèm số khách, mới sửa gần nhất trước."""

    def __init__(self, weddings: WeddingRepository, guests: GuestCounter) -> None:
        self._weddings = weddings
        self._guests = guests

    async def execute(self) -> list[StudioOverview]:
        weddings = await self._weddings.list_all()
        counts = await self._guests.count_by_tenant([item.tenant_id for item in weddings])
        return [
            StudioOverview(
                wedding=item,
                guest_count=counts.get(item.tenant_id, 0),
                main_date=_main_date(item),
            )
            for item in weddings
        ]


__all__ = ["ListStudios", "StudioOverview"]
