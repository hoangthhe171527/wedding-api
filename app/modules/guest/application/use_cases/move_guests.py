"""Use case: chuyển nhiều khách sang một link (thanh thao tác hàng loạt)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.core.context import ActorContext
from app.modules.guest.application.support import ensure_link
from app.modules.guest.domain.repositories import GuestRepository, InviteLinkRepository


class MoveGuestsToLink:
    def __init__(self, guests: GuestRepository, links: InviteLinkRepository) -> None:
        self._guests = guests
        self._links = links

    async def execute(self, actor: ActorContext, guest_ids: Sequence[UUID], link: str) -> int:
        """Raises: ValidationError (link lạ). Khách ngoài xưởng bị bỏ qua (không đếm)."""
        await ensure_link(self._links, actor.tenant_id, link)
        return await self._guests.set_link(actor.tenant_id, guest_ids, link, actor_id=actor.user_id)


__all__ = ["MoveGuestsToLink"]
