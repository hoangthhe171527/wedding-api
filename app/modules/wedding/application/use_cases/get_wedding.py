"""Use case: thông tin cưới của xưởng đang đăng nhập."""

from __future__ import annotations

from app.core.context import ActorContext
from app.modules.wedding.application.support import require_wedding
from app.modules.wedding.domain.entities import Wedding
from app.modules.wedding.domain.repositories import WeddingRepository


class GetWedding:
    """Đọc đám cưới trong phạm vi xưởng của actor."""

    def __init__(self, weddings: WeddingRepository) -> None:
        self._weddings = weddings

    async def execute(self, actor: ActorContext) -> Wedding:
        """Raises: NotFoundError(`wedding_not_setup`) nếu xưởng chưa khởi tạo."""
        return await require_wedding(self._weddings, actor.tenant_id)


__all__ = ["GetWedding"]
