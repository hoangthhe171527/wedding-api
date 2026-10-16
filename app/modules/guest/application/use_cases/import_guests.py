"""Use case: "Nhập nhanh nhiều khách" — dán nhiều dòng, mỗi dòng một thiệp."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.core.context import ActorContext
from app.core.errors import ValidationError
from app.modules.guest.application.ports import PlanGuestLimit
from app.modules.guest.application.support import (
    create_many_with_codes,
    ensure_capacity,
    settle_capacity,
)
from app.modules.guest.application.use_cases.links import CreateLink, LinkInput
from app.modules.guest.domain.entities import Guest, GuestDraft
from app.modules.guest.domain.repositories import GuestRepository, InviteLinkRepository
from app.modules.guest.domain.services import parse_import_rows


@dataclass(frozen=True, slots=True)
class ImportResult:
    created: list[Guest]
    skipped: int


class ImportGuests:
    """Đọc văn bản dán vào rồi tạo từng thiệp. Cột 4 là tên link: trùng tên link có sẵn
    (không phân biệt hoa thường) thì xếp vào đó; tên mới thì tạo link dùng mẫu chính."""

    def __init__(
        self,
        guests: GuestRepository,
        links: InviteLinkRepository,
        create_link: CreateLink,
        plan_limit: PlanGuestLimit | None = None,
    ) -> None:
        self._guests = guests
        self._links = links
        self._create_link = create_link
        self._plan_limit = plan_limit

    async def execute(self, actor: ActorContext, text: str) -> ImportResult:
        """Raises: ValidationError khi không đọc được dòng nào; ConflictError khi quá số link."""
        rows, skipped = parse_import_rows(text)
        if not rows:
            message = "Không đọc được dòng nào. Kiểm tra dấu | giữa các cột."
            raise ValidationError(message, code="import_empty", errors={"text": [message]})
        await ensure_capacity(self._guests, actor.tenant_id, len(rows), self._plan_limit)
        by_name = {
            link.name.strip().casefold(): str(link.id)
            for link in await self._links.list_all(actor.tenant_id)
        }
        drafts: list[GuestDraft] = []
        for draft, link_name in rows:
            key = link_name.casefold()
            if key and key not in by_name:
                created_link = await self._create_link.execute(actor, LinkInput(name=link_name))
                by_name[key] = str(created_link.id)
            drafts.append(replace(draft, link=by_name.get(key, "")))
        created = await create_many_with_codes(
            self._guests, actor.tenant_id, drafts, actor_id=actor.user_id
        )
        await settle_capacity(self._guests, actor.tenant_id, created, self._plan_limit)
        return ImportResult(created=created, skipped=skipped)


__all__ = ["ImportGuests", "ImportResult"]
