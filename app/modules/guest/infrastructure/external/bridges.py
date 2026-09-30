"""Cầu nối `guest` công bố cho module khác.

* `wedding` cần nạp khách mẫu (`GuestSeeder`) và đếm khách (`GuestCounter`).
* `invitation` cần tra một khách theo mã, một link đối tượng theo đuôi (`GuestByCodeReader`).

Bên dùng khai cổng; `guest` — chủ sở hữu dữ liệu — viết bản hiện thực ở đây và
chỉ trả dữ liệu thuần (không trả thực thể của mình, §1.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.modules.guest.application.use_cases import (
    LeaveWish,
    Reply,
    RespondToInvitation,
    SeedSampleGuests,
)
from app.modules.guest.domain.enums import RsvpStatus
from app.modules.guest.domain.services import is_valid_code, is_valid_link_slug
from app.modules.guest.infrastructure.persistence.repositories import (
    BeanieGuestRepository,
    BeanieInviteLinkRepository,
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
        self._links = BeanieInviteLinkRepository()

    async def by_link(self, tenant_id: UUID, slug: str) -> dict[str, Any] | None:
        """Link đối tượng theo đuôi: đuôi, mẫu, người được mời, lễ tiệc — KHÔNG trả tên
        link (nhãn nội bộ của cặp đôi)."""
        slug = slug.strip().lower()
        if not is_valid_link_slug(slug):
            return None
        link = await self._links.find_by_slug(tenant_id, slug)
        if link is None:
            return None
        return {
            "slug": link.slug,
            "template": link.template,
            "greeting": link.greeting,
            "events": list(link.events),
        }

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
        self._links = BeanieInviteLinkRepository()

    async def usage(self, tenant_id: UUID) -> dict[str, Any]:
        """Mẫu đang dùng gồm cả mẫu gán cho link đối tượng — người mở link thấy chúng."""
        count, templates, groups = await self._guests.usage(tenant_id)
        templates |= await self._links.templates(tenant_id)
        return {"count": count, "templates": sorted(templates), "groups": sorted(groups)}


class GuestResponder:
    """Nhận phản hồi từ web thiệp công khai và đọc lời chúc để hiện lên thiệp.

    `invitation` đã tra xưởng theo slug; cầu nối này KHÔNG trả thông tin khách
    nào khác ngoài chính lời chúc (tên người chúc, lời chúc, thời điểm).
    """

    def __init__(self) -> None:
        self._wishes = BeanieWishRepository()
        self._guests = BeanieGuestRepository()
        self._links = BeanieInviteLinkRepository()
        self._respond = RespondToInvitation(self._guests, self._wishes)

    async def respond(
        self,
        tenant_id: UUID,
        *,
        code: str,
        name: str,
        status: str,
        count: int,
        message: str,
        link: str = "",
    ) -> dict[str, Any]:
        known = await self._known_link(tenant_id, link)
        wish = await self._respond.execute(
            tenant_id,
            Reply(
                code=code,
                name=name,
                status=RsvpStatus(status),
                count=count,
                message=message,
                link=known,
            ),
        )
        return {"name": wish.name, "status": wish.status.value, "count": wish.count}

    async def wish(self, tenant_id: UUID, *, name: str, message: str) -> dict[str, Any]:
        wish = await LeaveWish(self._wishes).execute(tenant_id, name=name, message=message)
        return {"name": wish.name}

    async def record_open(self, tenant_id: UUID, code: str) -> bool:
        code = code.strip().lower()
        if not is_valid_code(code):
            return False
        return await self._guests.record_open(tenant_id, code)

    async def record_link_open(self, tenant_id: UUID, slug: str) -> bool:
        known = await self._known_link(tenant_id, slug)
        return await self._links.record_open(tenant_id, known) if known else False

    async def _known_link(self, tenant_id: UUID, slug: str) -> str:
        """Đuôi link có thật trong xưởng, hoặc rỗng — không ghi đuôi bịa vào sổ phản hồi."""
        slug = slug.strip().lower()
        if not slug or not is_valid_link_slug(slug):
            return ""
        return slug if await self._links.find_by_slug(tenant_id, slug) else ""

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
