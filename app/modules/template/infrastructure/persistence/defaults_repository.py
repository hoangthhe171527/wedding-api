"""Đọc / ghi mặc định hệ thống (`catalog_defaults`)."""

from __future__ import annotations

import time
from uuid import UUID

from app.core.base_model import utc_now
from app.modules.template.domain.defaults import CatalogDefaults
from app.modules.template.infrastructure.persistence.models import CatalogDefaultsDocument

_KEY = "system"

#: Một bản ghi toàn hệ thống, đọc ở MỌI lượt mở web thiệp: giữ trong tiến trình ngắn
#: hạn. Lưu thì xoá ngay trong tiến trình đó; worker khác thấy bản mới sau tối đa TTL.
_TTL_SECONDS = 60.0
_cached: tuple[float, CatalogDefaults] | None = None


class BeanieCatalogDefaultsRepository:
    async def get(self) -> CatalogDefaults:
        global _cached
        now = time.monotonic()
        if _cached is not None and now - _cached[0] < _TTL_SECONDS:
            return _cached[1]
        value = await self._load()
        _cached = (now, value)
        return value

    async def _load(self) -> CatalogDefaults:
        doc = await CatalogDefaultsDocument.find_one({"key": _KEY})
        if doc is None:
            return CatalogDefaults()
        return CatalogDefaults(
            group_templates=dict(doc.group_templates),
            default_template=doc.default_template,
            wording={tone: dict(fields) for tone, fields in doc.wording.items()},
            messages=dict(doc.messages),
        )

    async def save(self, defaults: CatalogDefaults, *, actor_id: UUID) -> CatalogDefaults:
        now = utc_now()
        await CatalogDefaultsDocument.get_motor_collection().update_one(
            {"key": _KEY},
            {
                "$set": {
                    "group_templates": defaults.group_templates,
                    "default_template": defaults.default_template,
                    "wording": defaults.wording,
                    "messages": defaults.messages,
                    "updated_at": now,
                    "updated_by": actor_id,
                },
                "$setOnInsert": {"_id": CatalogDefaultsDocument().id, "created_at": now},
            },
            upsert=True,
        )
        global _cached
        _cached = None
        return defaults


__all__ = ["BeanieCatalogDefaultsRepository", "clear_defaults_cache"]


def clear_defaults_cache() -> None:
    """Xoá cache trong tiến trình — cho test (DB được dọn giữa các bài)."""
    global _cached
    _cached = None
