"""Chuyển đổi một lần sang design theo mẫu + khách theo link (spec §8).

Chạy tự động lúc API khởi động (idempotent: đám cưới có `schema_version >= 1` bị bỏ
qua), hoặc tay: `python -m app.seeds.migrate_links_designs`.

Nhiều worker uvicorn cùng khởi động cùng chạy hàm này: mỗi đám cưới được "nhận"
nguyên tử (`migrating_at`, hết hạn sau 10 phút) trước khi chuyển, nên không bao giờ
hai worker cùng chuyển một đám cưới.

Mỗi đám cưới:
1. `default_template` -> khoá chuẩn (mẫu đã nghỉ -> `daile`);
   `designs[mẫu chính]` <- trường giao diện cũ (nếu chưa có).
2. Link có sẵn mà `template` rỗng -> điền mẫu chính. Video riêng của link (`intro`)
   không còn được đọc — chỉ đếm vào log.
3. Khách chưa có link được gom theo (nhóm, mẫu, lễ tiệc khách đang thấy) -> mỗi
   gom một link. Lễ tiệc khách đang thấy tính như web thiệp (`eventsFor`): danh sách
   riêng (chỉ id còn tồn tại), nếu rỗng thì lễ tiệc của nhà khách + chung, nếu vẫn rỗng
   thì tất cả. Link lưu `events = []` khi trùng toàn bộ lễ tiệc của đám cưới.
   Cùng (nhóm, mẫu) mà ra nhiều gom -> hậu tố " – Nhà trai"/" – Nhà gái" (khi cả gom
   cùng nhà và đúng mặc định của nhà) hoặc " – 2", " – 3"...
4. Mọi mẫu phụ đang dùng (mẫu của link, mẫu nhóm có khách, mẫu riêng của khách — theo
   khoá chuẩn) chưa có design -> chép giao diện chung cũ: khách thấy y như trước.
Mã khách và đuôi link cũ không đổi, nên link đã gửi vẫn mở đúng người.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict
from datetime import timedelta
from typing import Any
from uuid import UUID

from pymongo import ReturnDocument

from app.core.base_model import utc_now
from app.core.logging import get_logger
from app.modules.guest.domain.services import (
    LINK_NAME_MAX,
    LINK_SLUG_MAX,
    is_valid_link_slug,
    link_slug_from,
)
from app.modules.guest.infrastructure.persistence.models import GuestDocument, InviteLinkDocument
from app.modules.template.domain.catalog import canonical_template_key
from app.modules.template.infrastructure.persistence.models import TemplateDocument
from app.modules.wedding.infrastructure.persistence.models import SCHEMA_VERSION, WeddingDocument

log = get_logger(__name__)

_LOOK_KEYS = ("theme", "card_design", "intro", "open_style", "music_url")
#: Worker nhận đám cưới rồi chết giữa chừng: sau chừng này worker khác được nhận lại.
CLAIM_TTL = timedelta(minutes=10)
_SIDE_LABELS = {"trai": "Nhà trai", "gai": "Nhà gái"}


async def _template_name(key: str) -> str:
    doc = await TemplateDocument.find_one({"key": key})
    return doc.name if doc else key


def _unique(base: str, taken: set[str]) -> str:
    """Đuôi link chưa dùng và hợp lệ (2-40 ký tự); tên rỗng hoặc quá ngắn dùng "link"."""
    root = base if is_valid_link_slug(base) else "link"
    slug, n = root, 1
    while slug in taken:
        n += 1
        suffix = f"-{n}"
        slug = f"{root[: LINK_SLUG_MAX - len(suffix)].rstrip('-')}{suffix}"
    taken.add(slug)
    return slug


def _side_default(events: list[dict[str, Any]], side: str) -> tuple[str, ...]:
    """Lễ tiệc của một nhà: sự kiện của nhà đó + chung; rỗng thì tất cả."""
    ids = [e["id"] for e in events if e.get("side") in (side, "chung")]
    return tuple(sorted(ids or [e["id"] for e in events]))


def _effective_events(events: list[dict[str, Any]], guest: dict[str, Any]) -> tuple[str, ...]:
    """Lễ tiệc khách thấy trước khi chuyển (gương `eventsFor` ở web thiệp)."""
    existing = {e["id"] for e in events}
    chosen = list(guest.get("events") or [])
    if chosen:
        # Danh sách riêng mà mọi id đã bị xoá: `eventsFor` lùi về TẤT CẢ lễ tiệc.
        explicit = {event for event in chosen if event in existing}
        return tuple(sorted(explicit or existing))
    return _side_default(events, str(guest.get("side") or "trai"))


async def migrate_wedding(raw: dict[str, Any]) -> dict[str, int]:
    tenant_id: UUID = raw["tenant_id"]
    default_template = canonical_template_key(str(raw.get("default_template") or ""))
    main = default_template or "daile"
    look = {key: raw.get(key) for key in _LOOK_KEYS if key in raw}
    designs: dict[str, Any] = dict(raw.get("designs") or {})
    designs.setdefault(main, look)

    links_col = InviteLinkDocument.get_motor_collection()
    guests_col = GuestDocument.get_motor_collection()
    live = {"tenant_id": tenant_id, "deleted_at": None}
    intros_dropped = int(await links_col.count_documents({**live, "intro": {"$nin": ["", None]}}))
    await links_col.update_many(
        {**live, "template": {"$in": ["", None]}}, {"$set": {"template": main}}
    )
    taken = {str(slug) for slug in await links_col.distinct("slug", {"tenant_id": tenant_id})}

    events: list[dict[str, Any]] = list(raw.get("events") or [])
    all_ids = tuple(sorted(e["id"] for e in events))
    group_templates: dict[str, str] = raw.get("group_templates") or {}
    # Mẫu phụ khách đang thấy: mẫu nhóm có khách + mẫu riêng của khách (+ mẫu link, dưới).
    in_use: set[str] = set()
    async for guest in guests_col.find(live, {"group": 1, "template": 1}):
        group = str(guest.get("group") or "Bạn bè")
        in_use.add(canonical_template_key(group_templates.get(group) or main))
        if guest.get("template"):
            in_use.add(canonical_template_key(str(guest["template"])))
    buckets: dict[tuple[str, str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    async for guest in guests_col.find({**live, "link": {"$in": ["", None]}}):
        group = str(guest.get("group") or "Bạn bè")
        group_tpl = canonical_template_key(group_templates.get(group) or main)
        own = canonical_template_key(str(guest.get("template") or "")) or group_tpl
        buckets[(group, own, _effective_events(events, guest))].append(guest)

    by_pair: dict[tuple[str, str], list[tuple[str, ...]]] = defaultdict(list)
    for group, template, effective in buckets:
        by_pair[(group, template)].append(effective)

    created = 0
    now = utc_now()
    for (group, template), variants in by_pair.items():
        group_tpl = canonical_template_key(group_templates.get(group) or main)
        base = group if template == group_tpl else f"{group} – {await _template_name(template)}"
        counter = 1
        for effective in sorted(variants):
            members = buckets[(group, template, effective)]
            name = base
            if len(variants) > 1:
                sides = {str(g.get("side") or "trai") for g in members}
                side = next(iter(sides))
                if (
                    len(sides) == 1
                    and side in _SIDE_LABELS
                    and effective == _side_default(events, side)
                ):
                    name = f"{base} – {_SIDE_LABELS[side]}"
                else:
                    counter += 1
                    name = f"{base} – {counter}"
            name = name[:LINK_NAME_MAX].strip()
            link = InviteLinkDocument(
                tenant_id=tenant_id,
                slug=_unique(link_slug_from(name), taken),
                name=name,
                template=template,
                events=[] if effective == all_ids else list(effective),
            )
            link.stamp_created(None)
            await link.insert()
            created += 1
            await guests_col.update_many(
                {"tenant_id": tenant_id, "_id": {"$in": [guest["_id"] for guest in members]}},
                {"$set": {"link": str(link.id), "updated_at": now}},
            )

    for template in await links_col.distinct("template", live):
        in_use.add(canonical_template_key(str(template or "")) or main)
    for template in sorted(in_use - {main}):
        designs.setdefault(template, look)

    await WeddingDocument.get_motor_collection().update_one(
        {"_id": raw["_id"]},
        {
            "$set": {
                "default_template": default_template,
                "designs": designs,
                "schema_version": SCHEMA_VERSION,
            },
            "$unset": {"migrating_at": ""},
        },
    )
    log.info(
        "links_designs_migrated",
        tenant_id=str(tenant_id),
        links_created=created,
        intro_overrides_dropped=intros_dropped,
    )
    return {"links_created": created, "intro_overrides_dropped": intros_dropped}


def _pending() -> dict[str, Any]:
    return {"deleted_at": None, "schema_version": {"$not": {"$gte": SCHEMA_VERSION}}}


async def _claim(wedding_id: Any) -> dict[str, Any] | None:
    """Nhận một đám cưới để chuyển; None = đã chuyển xong hoặc worker khác đang chuyển."""
    now = utc_now()
    collection = WeddingDocument.get_motor_collection()
    claimed: dict[str, Any] | None = await collection.find_one_and_update(
        {
            "_id": wedding_id,
            **_pending(),
            "$or": [{"migrating_at": None}, {"migrating_at": {"$lt": now - CLAIM_TTL}}],
        },
        {"$set": {"migrating_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    return claimed


async def run() -> dict[str, int]:
    """Chuyển mọi đám cưới chưa chuyển. Trả số đám cưới đã chuyển, số link tạo, số lỗi."""
    total = {"weddings": 0, "links_created": 0, "intro_overrides_dropped": 0, "failed": 0}
    collection = WeddingDocument.get_motor_collection()
    ids = [raw["_id"] async for raw in collection.find(_pending(), {"_id": 1})]
    for wedding_id in ids:
        raw = await _claim(wedding_id)
        if raw is None:
            continue
        try:
            result = await migrate_wedding(raw)
        except Exception:
            # Một đám cưới hỏng không được làm API không khởi động; lần khởi động sau thử lại.
            log.exception("links_designs_migration_failed", tenant_id=str(raw.get("tenant_id")))
            total["failed"] += 1
            # Trả quyền nhận ngay; trả không được thì quyền tự hết hạn sau `CLAIM_TTL`.
            with contextlib.suppress(Exception):
                await collection.update_one({"_id": wedding_id}, {"$unset": {"migrating_at": ""}})
            continue
        total["weddings"] += 1
        total["links_created"] += result["links_created"]
        total["intro_overrides_dropped"] += result["intro_overrides_dropped"]
    return total


if __name__ == "__main__":
    from app.core.database import init_database

    async def _main() -> None:
        await init_database()
        log.info("links_designs_migration_done", **await run())

    asyncio.run(_main())
