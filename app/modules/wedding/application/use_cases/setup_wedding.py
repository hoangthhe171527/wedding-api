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
from app.modules.wedding.application.ports import CatalogDefaults, GuestSeeder, PlanGate
from app.modules.wedding.domain.entities import Wedding, WeddingContent
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
        gate: PlanGate | None = None,
    ) -> None:
        self._weddings = weddings
        self._guests = guests
        self._defaults = defaults
        self._gate = gate

    async def execute(self, actor: ActorContext, mode: SetupMode) -> Wedding:
        """Raises: ConflictError nếu xưởng đã có đám cưới."""
        if await self._weddings.find_by_tenant(actor.tenant_id) is not None:
            raise self._exists()

        content = sample_content() if mode is SetupMode.SAMPLE else blank_content()
        if self._defaults is not None:
            content = await self._apply_system_defaults(actor, content)
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

    async def _apply_system_defaults(
        self, actor: ActorContext, content: WeddingContent
    ) -> WeddingContent:
        """Mẫu theo nhóm do đội vận hành đặt: xưởng mới nhận, tự đổi lại được.

        Chỉ nhận mẫu NẰM TRONG gói hiện tại của xưởng; mẫu vượt gói giữ mẫu miễn phí
        của bản mẫu — mặc định hệ thống không được làm xưởng mới bị chặn khi xuất bản.
        """
        assert self._defaults is not None
        system = await self._defaults.defaults()
        chosen = {
            group: str(key)
            for group, key in dict(system.get("group_templates") or {}).items()
            if key
        }
        default = str(system.get("default_template") or "")
        blocked = await self._templates_outside_plan(
            actor, {*chosen.values(), *([default] if default else [])}
        )
        groups = dict(content.group_templates)
        groups.update({group: key for group, key in chosen.items() if key not in blocked})
        if default and default not in blocked:
            content = replace(content, default_template=default)
        return replace(content, group_templates=groups)

    async def _templates_outside_plan(self, actor: ActorContext, keys: set[str]) -> set[str]:
        if self._gate is None or not keys:
            return set()
        result = await self._gate.check(actor.tenant_id, {"templates": sorted(keys)})
        return {
            str(item.get("subject"))
            for item in result.get("violations") or []
            if item.get("code") == "template" and item.get("subject")
        }

    @staticmethod
    def _exists() -> ConflictError:
        return ConflictError("Xưởng đã có thông tin cưới.", code="wedding_exists")


__all__ = ["SetupMode", "SetupWedding"]
