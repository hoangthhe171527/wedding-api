"""Use case: gợi ý câu chữ cho một ô của thiệp (lời mời, câu báo tin...)."""

from __future__ import annotations

from app.core.context import ActorContext
from app.core.errors import ServiceUnavailableError, ValidationError
from app.modules.wedding.application.ports import WordingWriter
from app.modules.wedding.application.support import require_wedding
from app.modules.wedding.domain.enums import WORDING_KEYS, Tone
from app.modules.wedding.domain.repositories import WeddingRepository


class SuggestWording:
    def __init__(self, weddings: WeddingRepository, writer: WordingWriter) -> None:
        self._weddings = weddings
        self._writer = writer

    @property
    def enabled(self) -> bool:
        return self._writer.enabled

    async def execute(self, actor: ActorContext, *, field: str, tone: str) -> list[str]:
        """Raises: ServiceUnavailableError(`ai_disabled`), ValidationError, NotFoundError."""
        if not self._writer.enabled:
            raise ServiceUnavailableError(
                "Gợi ý bằng AI chưa được bật trên hệ thống.", code="ai_disabled"
            )
        if field not in WORDING_KEYS:
            raise ValidationError("Ô câu chữ không tồn tại.", code="wording_field")
        if tone not in {item.value for item in Tone}:
            raise ValidationError("Giọng văn không tồn tại.", code="wording_tone")
        content = (await require_wedding(self._weddings, actor.tenant_id)).content
        main = content.events[0] if content.events else None
        # Chỉ gửi những gì cần để viết câu chữ — không gửi khách mời, SĐT, số tài khoản.
        facts = {
            "chú rể": content.groom.short or content.groom.full,
            "cô dâu": content.bride.short or content.bride.full,
            "sự kiện chính": main.name if main else "",
            "ngày": main.date if main else "",
            "địa điểm": main.venue if main else "",
            "chuyện tình": content.story[:400],
        }
        current = content.wording.get(tone, {}).get(field, "")
        return await self._writer.suggest(
            field=field, tone=tone, facts={k: v for k, v in facts.items() if v}, current=current
        )


__all__ = ["SuggestWording"]
