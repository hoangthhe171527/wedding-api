"""Use case: đám cưới đang dùng những gì vượt gói (`GET /wedding/plan-check`).

Tab Xuất bản hiện danh sách này TRƯỚC khi khách bấm xuất bản, kèm gói thấp nhất
đủ dùng — thay vì để khách bấm rồi mới gặp lỗi.
"""

from __future__ import annotations

from typing import Any

from app.core.context import ActorContext
from app.modules.wedding.application.ports import GuestUsage, PlanGate
from app.modules.wedding.application.support import check_plan, require_wedding
from app.modules.wedding.domain.repositories import WeddingRepository


class CheckWeddingPlan:
    def __init__(self, weddings: WeddingRepository, guests: GuestUsage, gate: PlanGate) -> None:
        self._weddings = weddings
        self._guests = guests
        self._gate = gate

    async def execute(self, actor: ActorContext) -> dict[str, Any]:
        """Raises: NotFoundError(`wedding_not_setup`)."""
        wedding = await require_wedding(self._weddings, actor.tenant_id)
        return await check_plan(wedding, self._guests, self._gate)


__all__ = ["CheckWeddingPlan"]
