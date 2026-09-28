"""Use case: phản hồi và lời chúc khách gửi từ web thiệp.

* `RespondToInvitation` — khách (không đăng nhập) gửi "sẽ đến / chưa chắc /
  không đến", số người, lời chúc. Gọi qua cầu nối từ `invitation`, nơi đã tra
  xưởng theo slug công khai.
* `ListWishes` / `DeleteWish` — người soạn xem sổ phản hồi và gỡ lời chúc không
  muốn hiện trên web thiệp.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.modules.guest.domain.entities import Wish
from app.modules.guest.domain.enums import MAX_REPLY_PARTY, MAX_WISH_LENGTH, RsvpStatus
from app.modules.guest.domain.repositories import GuestRepository, WishRepository
from app.modules.guest.domain.services import is_valid_code

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Reply:
    """Một phản hồi từ web thiệp. `code` rỗng = khách mở link chung."""

    code: str
    name: str
    status: RsvpStatus
    count: int
    message: str


def _guest_line(title: str, name: str, plus: str) -> str:
    return " ".join(part for part in (title, name, plus) if part).strip()


class RespondToInvitation:
    def __init__(self, guests: GuestRepository, wishes: WishRepository) -> None:
        self._guests = guests
        self._wishes = wishes

    async def execute(self, tenant_id: UUID, reply: Reply) -> Wish:
        """Raises: ValidationError (thiếu tên ở link chung, trạng thái lạ, quá dài)."""
        if reply.status is RsvpStatus.NONE:
            raise ValidationError("Hãy chọn sẽ đến, chưa chắc hoặc không đến.", code="reply_status")
        message = reply.message.strip()[:MAX_WISH_LENGTH]
        count = min(max(reply.count, 1), MAX_REPLY_PARTY)
        code = reply.code.strip().lower()
        name = reply.name.strip()

        guest = None
        if code and is_valid_code(code):
            guest = await self._guests.record_reply(
                tenant_id, code, status=reply.status, count=count, message=message
            )
        if guest is not None:
            draft = guest.draft
            name = _guest_line(draft.title, draft.name, draft.plus)
            code = guest.code
        else:
            code = ""
            if not name:
                raise ValidationError(
                    "Hãy ghi tên để cô dâu chú rể biết bạn là ai.",
                    code="reply_name",
                    errors={"name": ["Nhập tên của bạn."]},
                )
        wish = await self._wishes.add(
            tenant_id,
            name=name[:160],
            message=message,
            status=reply.status,
            count=count,
            guest_code=code,
        )
        log.info("guest_replied", tenant_id=str(tenant_id), known=bool(code), status=reply.status)
        return wish


class LeaveWish:
    """Sổ lưu bút: khách chỉ gửi lời chúc, không xác nhận tham dự (trạng thái `none`)."""

    def __init__(self, wishes: WishRepository) -> None:
        self._wishes = wishes

    async def execute(self, tenant_id: UUID, *, name: str, message: str) -> Wish:
        """Raises: ValidationError (thiếu tên hoặc lời chúc)."""
        name = name.strip()[:160]
        message = message.strip()[:MAX_WISH_LENGTH]
        errors: dict[str, list[str]] = {}
        if not name:
            errors["name"] = ["Nhập tên của bạn."]
        if not message:
            errors["message"] = ["Nhập lời chúc."]
        if errors:
            raise ValidationError("Hãy ghi tên và lời chúc.", code="wish_invalid", errors=errors)
        wish = await self._wishes.add(
            tenant_id, name=name, message=message, status=RsvpStatus.NONE, count=1, guest_code=""
        )
        log.info("guest_wished", tenant_id=str(tenant_id))
        return wish


class ListWishes:
    def __init__(self, wishes: WishRepository) -> None:
        self._wishes = wishes

    async def execute(self, actor: ActorContext) -> list[Wish]:
        return await self._wishes.list_recent(actor.tenant_id, limit=500, with_message=False)


class DeleteWish:
    def __init__(self, wishes: WishRepository) -> None:
        self._wishes = wishes

    async def execute(self, actor: ActorContext, wish_id: UUID) -> None:
        """Raises: NotFoundError."""
        if not await self._wishes.soft_delete(actor.tenant_id, wish_id, actor_id=actor.user_id):
            raise NotFoundError("Không tìm thấy lời chúc.", code="wish_not_found")


__all__ = ["DeleteWish", "LeaveWish", "ListWishes", "Reply", "RespondToInvitation"]
