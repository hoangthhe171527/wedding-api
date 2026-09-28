"""Use case: thêm một khách mời."""

from __future__ import annotations

from app.core.context import ActorContext
from app.core.logging import get_logger
from app.modules.guest.application.ports import PlanGuestLimit, TemplateCatalog
from app.modules.guest.application.support import (
    create_with_code,
    ensure_capacity,
    ensure_valid,
    settle_capacity,
)
from app.modules.guest.domain.entities import Guest, GuestDraft
from app.modules.guest.domain.repositories import GuestRepository

log = get_logger(__name__)


class CreateGuest:
    """Tạo thiệp mời mới với mã khách riêng."""

    def __init__(
        self,
        guests: GuestRepository,
        templates: TemplateCatalog,
        plan_limit: PlanGuestLimit | None = None,
    ) -> None:
        self._guests = guests
        self._templates = templates
        self._plan_limit = plan_limit

    async def execute(self, actor: ActorContext, draft: GuestDraft) -> Guest:
        """Raises: ValidationError, ConflictError (vượt số thiệp tối đa)."""
        ensure_valid(draft, await self._templates.known_keys())
        await ensure_capacity(self._guests, actor.tenant_id, 1, self._plan_limit)
        guest = await create_with_code(self._guests, actor.tenant_id, draft, actor_id=actor.user_id)
        await settle_capacity(self._guests, actor.tenant_id, [guest], self._plan_limit)
        log.info("guest_created", tenant_id=str(actor.tenant_id), code=guest.code)
        return guest


__all__ = ["CreateGuest"]
