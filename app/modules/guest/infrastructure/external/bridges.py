"""Cầu nối `guest` công bố cho module khác.

* `wedding` cần nạp khách mẫu (`GuestSeeder`) và đếm khách (`GuestCounter`).
* `invitation` cần tra một khách theo mã (`GuestByCodeReader`).

Bên dùng khai cổng; `guest` — chủ sở hữu dữ liệu — viết bản hiện thực ở đây và
chỉ trả dữ liệu thuần (không trả thực thể của mình, §1.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.modules.guest.application.use_cases import Reply, RespondToInvitation, SeedSampleGuests
from app.modules.guest.domain.enums import RsvpStatus
from app.modules.guest.domain.services import is_valid_code
from app.modules.guest.infrastructure.persistence.repositories import (
    BeanieGuestRepository,
    BeanieWishRepository,
)


class GuestCounter:
    """Đếm khách còn hiệu lực theo xưởng."""

    def __init__(self) -> None:
        self._guests = BeanieGuestRepository()

    async def count_by_tenant(self, tenant_ids: Sequence[UUID]) -> dict[UUID, int]:
        return await self._guests.count_by_tenant(tenant_ids)


class GuestByCodeReader:
    """Tra một khách theo mã trong một xưởng đã biết (xưởng suy từ slug công khai).

    Chỉ trả những gì thiệp cần để chào đúng người — KHÔNG trả ghi chú nội bộ,
    trạng thái gửi thiệp hay phản hồi.
    """

    def __init__(self) -> None:
        self._guests = BeanieGuestRepository()

    async def by_code(self, tenant_id: UUID, code: str) -> dict[str, Any] | None:
        code = code.strip().lower()
        if not is_valid_code(code):
            return None
        guest = await self._guests.find_by_code(tenant_id, code)
        if guest is None:
            return None
        draft = guest.draft
        return {
            "code": guest.code,
            "title": draft.title,
            "name": draft.name,
            "plus": draft.plus,
            "group": draft.group,
            "side": draft.side.value,
            "events": list(draft.events),
            "count": draft.count,
            "template": draft.template,
        }


class GuestUsageReader:
    """Khách của một xưởng đang dùng gì — để `wedding` xét gói trước khi xuất bản."""

    def __init__(self) -> None:
        self._guests = BeanieGuestRepository()

    async def usage(self, tenant_id: UUID) -> dict[str, Any]:
        count, templates, groups = await self._guests.usage(tenant_id)
        return {"count": count, "templates": sorted(templates), "groups": sorted(groups)}


class GuestResponder:
    """Nhận phản hồi từ web thiệp công khai và đọc lời chúc để hiện lên thiệp.

    `invitation` đã tra xưởng theo slug; cầu nối này KHÔNG trả thông tin khách
    nào khác ngoài chính lời chúc (tên người chúc, lời chúc, thời điểm).
    """

    def __init__(self) -> None:
        self._wishes = BeanieWishRepository()
        self._guests = BeanieGuestRepository()
        self._respond = RespondToInvitation(self._guests, self._wishes)

    async def respond(
        self, tenant_id: UUID, *, code: str, name: str, status: str, count: int, message: str
    ) -> dict[str, Any]:
        wish = await self._respond.execute(
            tenant_id,
            Reply(code=code, name=name, status=RsvpStatus(status), count=count, message=message),
        )
        return {"name": wish.name, "status": wish.status.value, "count": wish.count}

    async def record_open(self, tenant_id: UUID, code: str) -> bool:
        code = code.strip().lower()
        if not is_valid_code(code):
            return False
        return await self._guests.record_open(tenant_id, code)

    async def public_wishes(self, tenant_id: UUID, limit: int) -> list[dict[str, Any]]:
        wishes = await self._wishes.list_recent(tenant_id, limit=limit, with_message=True)
        return [
            {"name": item.name, "message": item.message, "created_at": item.created_at}
            for item in wishes
        ]


def build_guest_seeder(*, fixed_codes: bool = False) -> SeedSampleGuests:
    """`fixed_codes=True` chỉ cho xưởng demo của seed (link demo ổn định)."""
    return SeedSampleGuests(BeanieGuestRepository(), fixed_codes=fixed_codes)


def build_guest_counter() -> GuestCounter:
    return GuestCounter()


def build_guest_by_code_reader() -> GuestByCodeReader:
    return GuestByCodeReader()


def build_guest_usage_reader() -> GuestUsageReader:
    return GuestUsageReader()


def build_guest_responder() -> GuestResponder:
    return GuestResponder()


__all__ = [
    "GuestByCodeReader",
    "GuestCounter",
    "GuestResponder",
    "GuestUsageReader",
    "build_guest_by_code_reader",
    "build_guest_counter",
    "build_guest_responder",
    "build_guest_seeder",
    "build_guest_usage_reader",
]
