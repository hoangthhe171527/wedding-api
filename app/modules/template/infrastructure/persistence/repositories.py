"""Hiện thực Beanie của `TemplateRepository`."""

from __future__ import annotations

from typing import Any

from pymongo.errors import DuplicateKeyError

from app.core.base_model import utc_now
from app.modules.template.domain.entities import Template
from app.modules.template.domain.enums import Family, Layout, Tier, Tone
from app.modules.template.infrastructure.persistence.models import TemplateDocument


def _template(doc: TemplateDocument) -> Template:
    return Template(
        key=doc.key,
        name=doc.name,
        family=Family(doc.family),
        tone=Tone(doc.tone),
        layout=Layout(doc.layout),
        is_new=doc.is_new,
        is_active=doc.is_active,
        sort_order=doc.sort_order,
        tier=Tier(doc.tier),
    )


class BeanieTemplateRepository:
    """`TemplateRepository` trên Mongo."""

    async def list_all(self, *, include_inactive: bool) -> list[Template]:
        criteria: dict[str, Any] = {} if include_inactive else {"is_active": True}
        docs = await TemplateDocument.find(criteria).sort("+sort_order").to_list()
        return [_template(doc) for doc in docs]

    async def find(self, key: str) -> Template | None:
        doc = await TemplateDocument.find_one(TemplateDocument.key == key)
        return _template(doc) if doc else None

    async def keys(self) -> frozenset[str]:
        raw = await TemplateDocument.get_motor_collection().distinct("key")
        return frozenset(str(item) for item in raw)

    async def insert_missing(self, blueprints: tuple[Template, ...]) -> int:
        existing = await self.keys()
        created = 0
        for item in blueprints:
            if item.key in existing:
                continue
            try:
                await TemplateDocument(
                    key=item.key,
                    name=item.name,
                    family=item.family.value,
                    tone=item.tone.value,
                    layout=item.layout.value,
                    is_new=item.is_new,
                    sort_order=item.sort_order,
                    tier=item.tier.value,
                ).insert()
                created += 1
            except DuplicateKeyError:
                continue  # tiến trình khác vừa seed cùng mẫu
        return created

    async def backfill_tiers(self, blueprints: tuple[Template, ...]) -> int:
        """Gắn hạng cho mẫu tạo TRƯỚC khi có khái niệm hạng (thiếu trường `tier`).

        Chỉ chạm document chưa có trường: hạng đội vận hành đã chỉnh giữ nguyên.
        """
        collection = TemplateDocument.get_motor_collection()
        fixed = 0
        for item in blueprints:
            result = await collection.update_one(
                {"key": item.key, "tier": {"$exists": False}},
                {"$set": {"tier": item.tier.value, "updated_at": utc_now()}},
            )
            fixed += int(result.modified_count)
        return fixed

    async def tiers(self) -> dict[str, Tier]:
        """Khoá mẫu -> hạng, kể cả mẫu đã tắt (thiệp đã gán vẫn phải xét được)."""
        rows = (
            await TemplateDocument.get_motor_collection()
            .find({}, {"key": 1, "tier": 1, "_id": 0})
            .to_list(None)
        )
        return {str(row["key"]): Tier(row.get("tier", Tier.STANDARD.value)) for row in rows}

    async def update_flags(
        self,
        key: str,
        *,
        is_active: bool | None = None,
        is_new: bool | None = None,
        sort_order: int | None = None,
        tier: Tier | None = None,
    ) -> Template | None:
        changes: dict[str, Any] = {
            name: value
            for name, value in (
                ("is_active", is_active),
                ("is_new", is_new),
                ("sort_order", sort_order),
                ("tier", tier.value if tier else None),
            )
            if value is not None
        }
        if changes:
            changes["updated_at"] = utc_now()
            await TemplateDocument.get_motor_collection().update_one(
                {"key": key}, {"$set": changes}
            )
        return await self.find(key)


__all__ = ["BeanieTemplateRepository"]
