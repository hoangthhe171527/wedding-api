"""Chuyển đổi một lần sang design theo mẫu + khách theo link (spec §8).

Chạy tự động lúc API khởi động (idempotent: đám cưới có `schema_version >= 1` bị bỏ
qua), hoặc tay: `python -m app.seeds.migrate_links_designs`.

Mỗi đám cưới:
1. `designs[mẫu chính]` <- trường giao diện cũ (nếu chưa có).
2. Link có sẵn mà `template` rỗng -> điền mẫu chính.
3. Mỗi nhóm khách đang có khách -> một link tên nhóm, mẫu = `group_templates[nhóm]`
   hoặc mẫu chính; khách có mẫu riêng khác mẫu nhóm -> link "<Nhóm> – <tên mẫu>".
   Lễ tiệc của link = hợp lễ tiệc của khách trong link (khách mời theo nhà: rỗng).
Mã khách và đuôi link cũ không đổi, nên link đã gửi vẫn mở đúng người.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from uuid import UUID

from app.core.base_model import utc_now
from app.core.logging import get_logger
from app.modules.guest.domain.services import link_slug_from
from app.modules.guest.infrastructure.persistence.models import GuestDocument, InviteLinkDocument
from app.modules.template.domain.catalog import canonical_template_key
from app.modules.template.infrastructure.persistence.models import TemplateDocument
from app.modules.wedding.infrastructure.persistence.models import WeddingDocument

log = get_logger(__name__)

SCHEMA_VERSION = 1
_LOOK_KEYS = ("theme", "card_design", "intro", "open_style", "music_url")


async def _template_name(key: str) -> str:
    doc = await TemplateDocument.find_one({"key": key})
    return doc.name if doc else key


def _unique(base: str, taken: set[str]) -> str:
    slug, n = base or "link", 1
    while slug in taken:
        n += 1
        slug = f"{base}-{n}"
    taken.add(slug)
    return slug


async def migrate_wedding(raw: dict[str, Any]) -> dict[str, int]:
    tenant_id: UUID = raw["tenant_id"]
    main = canonical_template_key(raw.get("default_template") or "") or "daile"
    designs: dict[str, Any] = dict(raw.get("designs") or {})
    designs.setdefault(main, {key: raw.get(key) for key in _LOOK_KEYS if key in raw})

    links_col = InviteLinkDocument.get_motor_collection()
    guests_col = GuestDocument.get_motor_collection()
    live = {"tenant_id": tenant_id, "deleted_at": None}
    await links_col.update_many({**live, "template": ""}, {"$set": {"template": main}})
    taken = {str(slug) for slug in await links_col.distinct("slug", {"tenant_id": tenant_id})}

    group_templates: dict[str, str] = raw.get("group_templates") or {}
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    async for guest in guests_col.find({**live, "link": {"$in": ["", None]}}):
        group = str(guest.get("group") or "Bạn bè")
        group_tpl = canonical_template_key(group_templates.get(group) or main)
        own = canonical_template_key(str(guest.get("template") or "")) or group_tpl
        buckets[(group, own)].append(guest)

    created = 0
    now = utc_now()
    for (group, template), members in buckets.items():
        group_tpl = canonical_template_key(group_templates.get(group) or main)
        name = group if template == group_tpl else f"{group} – {await _template_name(template)}"
        events = sorted({event for guest in members for event in guest.get("events") or []})
        link = InviteLinkDocument(
            tenant_id=tenant_id,
            slug=_unique(link_slug_from(name), taken),
            name=name,
            template=template,
            events=events,
        )
        link.stamp_created(None)
        await link.insert()
        created += 1
        await guests_col.update_many(
            {"_id": {"$in": [guest["_id"] for guest in members]}},
            {"$set": {"link": str(link.id), "updated_at": now}},
        )

    await WeddingDocument.get_motor_collection().update_one(
        {"_id": raw["_id"]}, {"$set": {"designs": designs, "schema_version": SCHEMA_VERSION}}
    )
    log.info("links_designs_migrated", tenant_id=str(tenant_id), links_created=created)
    return {"links_created": created}


async def run() -> dict[str, int]:
    """Chuyển mọi đám cưới chưa chuyển. Trả số đám cưới đã chuyển và số link đã tạo."""
    total = {"weddings": 0, "links_created": 0}
    cursor = WeddingDocument.get_motor_collection().find(
        {"deleted_at": None, "schema_version": {"$not": {"$gte": SCHEMA_VERSION}}}
    )
    async for raw in cursor:
        result = await migrate_wedding(raw)
        total["weddings"] += 1
        total["links_created"] += result["links_created"]
    return total


if __name__ == "__main__":
    from app.core.database import init_database

    async def _main() -> None:
        await init_database()
        log.info("links_designs_migration_done", **await run())

    asyncio.run(_main())
