"""Use case: đặt đường dẫn công khai và bật/tắt web thiệp (tab Xuất bản).

Thay cho bước "tải gói web rồi kéo thả lên Netlify" của thiết kế: hệ thống tự
phục vụ web thiệp tại `/invite/<slug>`. Đổi slug là đổi mọi link đã gửi — web
phải cảnh báo điều đó trước khi gọi.
"""

from __future__ import annotations

from app.core.context import ActorContext
from app.core.errors import ConflictError, ValidationError
from app.core.logging import get_logger
from app.modules.wedding.application.ports import GuestUsage, PlanGate
from app.modules.wedding.application.support import ensure_plan, not_setup, require_wedding
from app.modules.wedding.domain.entities import Wedding
from app.modules.wedding.domain.repositories import SlugTakenError, WeddingRepository
from app.modules.wedding.domain.services import slug_problem

log = get_logger(__name__)


class SetPublication:
    """Đổi slug và/hoặc trạng thái xuất bản."""

    def __init__(self, weddings: WeddingRepository, guests: GuestUsage, gate: PlanGate) -> None:
        self._weddings = weddings
        self._guests = guests
        self._gate = gate

    async def execute(self, actor: ActorContext, *, slug: str, published: bool) -> Wedding:
        """Raises: ValidationError (slug sai), ConflictError (slug có chủ, vượt gói)."""
        slug = slug.strip().lower()
        problem = slug_problem(slug)
        if problem:
            raise ValidationError(problem, errors={"slug": [problem]})
        if published:
            await self._ensure_plan(actor)
        try:
            saved = await self._weddings.save_publication(
                actor.tenant_id, slug=slug, published=published, actor_id=actor.user_id
            )
        except SlugTakenError:
            message = "Đường dẫn này đã có người dùng. Hãy chọn tên khác."
            raise ConflictError(message, code="slug_taken", errors={"slug": [message]}) from None
        if saved is None:
            raise not_setup()
        log.info("wedding_publication", tenant_id=str(actor.tenant_id), published=published)
        return saved

    async def _ensure_plan(self, actor: ActorContext) -> None:
        """Soạn và xem trước thì dùng thoải mái; chỉ XUẤT BẢN mới phải hợp gói."""
        wedding = await require_wedding(self._weddings, actor.tenant_id)
        await ensure_plan(wedding, self._guests, self._gate)


__all__ = ["SetPublication"]
