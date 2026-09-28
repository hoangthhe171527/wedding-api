"""Use case: "Nhập nhanh nhiều khách" — dán nhiều dòng, mỗi dòng một thiệp."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.context import ActorContext
from app.core.errors import ValidationError
from app.modules.guest.application.ports import PlanGuestLimit
from app.modules.guest.application.support import (
    create_many_with_codes,
    ensure_capacity,
    settle_capacity,
)
from app.modules.guest.domain.entities import Guest
from app.modules.guest.domain.repositories import GuestRepository
from app.modules.guest.domain.services import parse_import


@dataclass(frozen=True, slots=True)
class ImportResult:
    created: list[Guest]
    skipped: int


class ImportGuests:
    """Đọc văn bản dán vào rồi tạo từng thiệp."""

    def __init__(self, guests: GuestRepository, plan_limit: PlanGuestLimit | None = None) -> None:
        self._guests = guests
        self._plan_limit = plan_limit

    async def execute(self, actor: ActorContext, text: str) -> ImportResult:
        """Raises: ValidationError khi không đọc được dòng nào."""
        drafts, skipped = parse_import(text)
        if not drafts:
            message = "Không đọc được dòng nào. Kiểm tra dấu | giữa các cột."
            raise ValidationError(message, code="import_empty", errors={"text": [message]})
        await ensure_capacity(self._guests, actor.tenant_id, len(drafts), self._plan_limit)
        created = await create_many_with_codes(
            self._guests, actor.tenant_id, drafts, actor_id=actor.user_id
        )
        await settle_capacity(self._guests, actor.tenant_id, created, self._plan_limit)
        return ImportResult(created=created, skipped=skipped)


__all__ = ["ImportGuests", "ImportResult"]
