"""Use case: đội vận hành chỉnh một mẫu (bật/tắt, nhãn Mới, thứ tự, hạng gói)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core import audit
from app.core.context import ActorContext
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.modules.template.domain.entities import Template
from app.modules.template.domain.enums import Tier
from app.modules.template.domain.repositories import TemplateRepository

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TemplatePatch:
    """Chỉ các trường gửi lên mới được đổi."""

    is_active: bool | None = None
    is_new: bool | None = None
    sort_order: int | None = None
    tier: Tier | None = None


class UpdateTemplate:
    """Cập nhật cờ của một mẫu."""

    def __init__(self, templates: TemplateRepository) -> None:
        self._templates = templates

    async def execute(self, actor: ActorContext, key: str, patch: TemplatePatch) -> Template:
        updated = await self._templates.update_flags(
            key,
            is_active=patch.is_active,
            is_new=patch.is_new,
            sort_order=patch.sort_order,
            tier=patch.tier,
        )
        if updated is None:
            raise NotFoundError("Không tìm thấy mẫu thiệp.")
        log.info("template_updated", key=key, by=str(actor.user_id))
        await audit.record(
            "template.updated",
            actor_id=actor.user_id,
            target_type="template",
            target_id=key,
            details={
                name: value
                for name, value in (
                    ("is_active", patch.is_active),
                    ("is_new", patch.is_new),
                    ("sort_order", patch.sort_order),
                    ("tier", patch.tier.value if patch.tier is not None else None),
                )
                if value is not None
            },
        )
        return updated


__all__ = ["TemplatePatch", "UpdateTemplate"]
