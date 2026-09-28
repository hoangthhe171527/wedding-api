"""Use case: khởi tạo đám cưới cho xưởng — "Lưu dữ liệu mẫu" hoặc "Bắt đầu trống".

Chép đúng luồng `seed(blank)` của thiết kế: xưởng mới xem dữ liệu mẫu nhưng chưa
lưu gì; bấm một trong hai nút thì đám cưới mới thật sự tồn tại. Chọn "mẫu" thì
kèm luôn danh sách khách mẫu (qua cổng `GuestSeeder` của module `guest`).
"""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum

from app.core.context import ActorContext
from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.modules.wedding.application.ports import CatalogDefaults, GuestSeeder
from app.modules.wedding.domain.entities import Wedding
from app.modules.wedding.domain.repositories import (
    SlugTakenError,
    WeddingAlreadyExistsError,
    WeddingRepository,
)
from app.modules.wedding.domain.samples import blank_content, sample_content
from app.modules.wedding.domain.services import couple_slug

log = get_logger(__name__)

#: Số lần thử thêm hậu tố khi slug gợi ý đã có chủ.
_SLUG_ATTEMPTS = 50


class SetupMode(StrEnum):
    SAMPLE = "sample"
    BLANK = "blank"


class SetupWedding:
    """Tạo đám cưới đầu tiên của xưởng."""

    def __init__(
        self,
        weddings: WeddingRepository,
        guests: GuestSeeder,
        defaults: CatalogDefaults | None = None,
    ) -> None:
        self._weddings = weddings
        self._guests = guests
        self._defaults = defaults

    async def execute(self, actor: ActorContext, mode: SetupMode) -> Wedding:
        """Raises: ConflictError nếu xưởng đã có đám cưới."""
        if await self._weddings.find_by_tenant(actor.tenant_id) is not None:
            raise self._exists()

        content = sample_content() if mode is SetupMode.SAMPLE else blank_content()
        if self._defaults is not None:
            # Mẫu theo nhóm khách do đội vận hành đặt: xưởng mới nhận, tự đổi lại được.
            system = await self._defaults.defaults()
            groups = {**content.group_templates, **dict(system.get("group_templates") or {})}
            content = replace(
                content,
                group_templates=groups,
                default_template=str(system.get("default_template") or "")
                or content.default_template,
            )
        base = couple_slug(content.groom.short, content.bride.short)
        wedding: Wedding | None = None
        for attempt in range(_SLUG_ATTEMPTS):
            slug = base if attempt == 0 else f"{base}-{attempt + 1}"
            if await self._weddings.slug_exists(slug):
                continue
            try:
                wedding = await self._weddings.create(
                    tenant_id=actor.tenant_id, content=content, slug=slug, actor_id=actor.user_id
                )
            except SlugTakenError:
                continue
            except WeddingAlreadyExistsError:
                raise self._exists() from None
            break
        if wedding is None:
            raise ConflictError("Chưa tạo được đường dẫn thiệp. Vui lòng thử lại.")

        if mode is SetupMode.SAMPLE:
            await self._guests.seed_sample(actor.tenant_id, actor_id=actor.user_id)
        log.info("wedding_setup", tenant_id=str(actor.tenant_id), mode=str(mode))
        return wedding

    @staticmethod
    def _exists() -> ConflictError:
        return ConflictError("Xưởng đã có thông tin cưới.", code="wedding_exists")


__all__ = ["SetupMode", "SetupWedding"]
