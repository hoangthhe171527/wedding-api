"""Use case: xoá một khách mời (xoá mềm — link riêng của khách ngừng hoạt động)."""

from __future__ import annotations

from uuid import UUID

from app.core.context import ActorContext
from app.core.logging import get_logger
from app.modules.guest.application.support import guest_not_found
from app.modules.guest.domain.repositories import GuestRepository

log = get_logger(__name__)


class DeleteGuest:
    """Xoá mềm trong phạm vi xưởng của actor."""

    def __init__(self, guests: GuestRepository) -> None:
        self._guests = guests

    async def execute(self, actor: ActorContext, guest_id: UUID) -> None:
        if not await self._guests.soft_delete(actor.tenant_id, guest_id, actor_id=actor.user_id):
            raise guest_not_found()
        log.info("guest_deleted", tenant_id=str(actor.tenant_id), guest_id=str(guest_id))


__all__ = ["DeleteGuest"]
