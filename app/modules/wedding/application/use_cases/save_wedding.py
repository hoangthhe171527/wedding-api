"""Use case: lưu nội dung đám cưới (`PUT /wedding`).

Form ở web lưu tự động sau mỗi lần ngừng gõ ~700ms, gửi TRỌN nội dung — y hệt
`flushW()` của thiết kế. Thay trọn thay vì vá từng trường: idempotent, gửi lại
bao nhiêu lần cũng ra cùng một trạng thái.
"""

from __future__ import annotations

from dataclasses import replace

from app.core.context import ActorContext
from app.modules.wedding.application.ports import GuestUsage, PlanGate, TemplateCatalog
from app.modules.wedding.application.support import ensure_plan, ensure_valid, not_setup
from app.modules.wedding.domain.entities import Wedding, WeddingContent
from app.modules.wedding.domain.repositories import WeddingRepository


class SaveWedding:
    """Thay nội dung đám cưới; không chạm slug, trạng thái xuất bản, tiến độ."""

    def __init__(
        self,
        weddings: WeddingRepository,
        templates: TemplateCatalog,
        guests: GuestUsage,
        gate: PlanGate,
    ) -> None:
        self._weddings = weddings
        self._templates = templates
        self._guests = guests
        self._gate = gate

    async def execute(self, actor: ActorContext, content: WeddingContent) -> Wedding:
        """Raises: ValidationError, NotFoundError, ConflictError(`plan_required`).

        Thiệp CHƯA xuất bản: soạn / xem trước mọi tính năng thoải mái. Thiệp ĐANG
        xuất bản: nội dung mới đi thẳng tới khách nên cũng phải hợp gói — nếu
        không, xuất bản một bản hợp lệ rồi sửa là dùng được mọi tính năng miễn phí.
        """
        ensure_valid(content, await self._templates.known_keys())
        current = await self._weddings.find_by_tenant(actor.tenant_id)
        if current is not None and current.published:
            await ensure_plan(replace(current, content=content), self._guests, self._gate)
        saved = await self._weddings.save_content(actor.tenant_id, content, actor_id=actor.user_id)
        if saved is None:
            raise not_setup()
        return saved


__all__ = ["SaveWedding"]
