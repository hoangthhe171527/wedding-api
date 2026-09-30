"""Use case: nạp danh mục mẫu khởi tạo (idempotent)."""

from __future__ import annotations

from app.modules.template.domain.catalog import RETIRED_KEYS, TEMPLATE_BLUEPRINTS
from app.modules.template.domain.repositories import TemplateRepository


class EnsureCatalog:
    """Tạo mẫu còn thiếu, tắt mẫu cho nghỉ; không đè mẫu đội vận hành đã chỉnh."""

    def __init__(self, templates: TemplateRepository) -> None:
        self._templates = templates

    async def execute(self) -> int:
        created = await self._templates.insert_missing(TEMPLATE_BLUEPRINTS)
        await self._templates.backfill_tiers(TEMPLATE_BLUEPRINTS)
        await self._templates.retire(frozenset(RETIRED_KEYS))
        return created


__all__ = ["EnsureCatalog"]
