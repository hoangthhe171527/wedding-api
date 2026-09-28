"""Tạo bản nhỏ (`SMALL_WIDTH`) cho ảnh tải lên TRƯỚC khi có bản nhỏ.

Chạy một lần sau khi nâng cấp: `python -m app.seeds.backfill_photo_variants`. Chạy lại
bao nhiêu lần cũng được — ảnh đã có `small_key`, ảnh hẹp hơn `SMALL_WIDTH` (không cần
bản nhỏ) và ảnh chưa lên kho object đều được bỏ qua. Chưa chạy thì web thiệp vẫn đúng:
`&w=sm` của ảnh chưa có bản nhỏ trả về bản đầy đủ.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.database import close_database, init_database
from app.core.logging import get_logger
from app.core.redis import close_redis
from app.core.storage import get_object_store
from app.modules.media.infrastructure.external.pillow_processor import (
    SMALL_WIDTH,
    PillowImageProcessor,
)
from app.modules.media.infrastructure.persistence.models import PhotoDocument
from app.modules.media.infrastructure.persistence.repositories import BeaniePhotoRepository

log = get_logger(__name__)


async def backfill_photo_variants() -> dict[str, Any]:
    store = get_object_store()
    photos = BeaniePhotoRepository(store)
    processor = PillowImageProcessor()
    created = missing = 0
    query = {
        "deleted_at": None,
        "storage_key": {"$ne": ""},
        "small_key": {"$in": ["", None]},
        "width": {"$gt": SMALL_WIDTH},
    }
    async for doc in PhotoDocument.find(query):
        data = await store.get(doc.storage_key)
        if data is None:
            missing += 1
            continue
        # Giải mã + thu nhỏ tốn CPU: ra thread, không làm đứng vòng sự kiện.
        small = await asyncio.to_thread(processor.small_variant, data)
        if small is not None and await photos.attach_small(doc.id, small):
            created += 1
    summary = {"created": created, "missing_objects": missing}
    log.info("photo_variants_backfilled", **summary)
    return summary


async def _main() -> None:
    await init_database()
    try:
        await backfill_photo_variants()
    finally:
        await close_redis()
        await close_database()


if __name__ == "__main__":
    asyncio.run(_main())
