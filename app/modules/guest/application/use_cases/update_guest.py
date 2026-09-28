"""Use case: sửa một khách mời (PATCH — chỉ trường gửi lên mới đổi).

Bảng khách đổi nhanh hai cột "Đã gửi" và "Phản hồi" ngay trên dòng; form trong
ngăn kéo gửi đủ mọi trường. Cả hai đi qua cùng một use case.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from uuid import UUID

from app.core.context import ActorContext
from app.modules.guest.application.ports import TemplateCatalog
from app.modules.guest.application.support import ensure_valid, guest_not_found
from app.modules.guest.domain.entities import Guest
from app.modules.guest.domain.enums import RsvpStatus, Side
from app.modules.guest.domain.repositories import GuestRepository


@dataclass(frozen=True, slots=True)
class GuestPatch:
    """Mỗi trường None = giữ nguyên."""

    name: str | None = None
    title: str | None = None
    plus: str | None = None
    group: str | None = None
    side: Side | None = None
    events: tuple[str, ...] | None = None
    count: int | None = None
    template: str | None = None
    status: RsvpStatus | None = None
    sent: bool | None = None
    note: str | None = None


class UpdateGuest:
    """Vá thiệp mời trong phạm vi xưởng của actor; ngoài phạm vi -> 404."""

    def __init__(self, guests: GuestRepository, templates: TemplateCatalog) -> None:
        self._guests = guests
        self._templates = templates

    async def execute(self, actor: ActorContext, guest_id: UUID, patch: GuestPatch) -> Guest:
        current = await self._guests.get(actor.tenant_id, guest_id)
        if current is None:
            raise guest_not_found()
        changes = {
            item.name: getattr(patch, item.name)
            for item in fields(patch)
            if getattr(patch, item.name) is not None
        }
        draft = replace(current.draft, **changes)
        ensure_valid(draft, await self._templates.known_keys())
        saved = await self._guests.replace(actor.tenant_id, guest_id, draft, actor_id=actor.user_id)
        if saved is None:
            raise guest_not_found()
        return saved


__all__ = ["GuestPatch", "UpdateGuest"]
