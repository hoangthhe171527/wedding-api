"""Use case: đánh dấu tiến độ lộ trình chuẩn bị (tab Kế hoạch)."""

from __future__ import annotations

from app.core.context import ActorContext
from app.modules.wedding.application.support import not_setup
from app.modules.wedding.domain.entities import Wedding
from app.modules.wedding.domain.repositories import WeddingRepository
from app.modules.wedding.domain.services import clean_checklist


class SaveChecklist:
    """Thay trọn tập việc đã xong."""

    def __init__(self, weddings: WeddingRepository) -> None:
        self._weddings = weddings

    async def execute(self, actor: ActorContext, done: dict[str, bool]) -> Wedding:
        saved = await self._weddings.save_checklist(
            actor.tenant_id, clean_checklist(done), actor_id=actor.user_id
        )
        if saved is None:
            raise not_setup()
        return saved


__all__ = ["SaveChecklist"]
