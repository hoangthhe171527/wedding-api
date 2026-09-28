"""Chuyển byte ảnh cũ từ Mongo (`photo_blobs`) sang kho object S3.

Chạy một lần sau khi nâng cấp: `python -m app.seeds.migrate_photos`. Chạy lại
bao nhiêu lần cũng được — ảnh đã có `storage_key` được bỏ qua; mỗi ảnh: ghi
object, gắn `storage_key`, rồi mới xoá blob trong Mongo.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.database import close_database, init_database
from app.core.logging import get_logger
from app.core.redis import close_redis
from app.core.storage import get_object_store
from app.modules.media.infrastructure.persistence.models import PhotoBlobDocument, PhotoDocument
from app.modules.media.infrastructure.persistence.repositories import photo_key

log = get_logger(__name__)


async def migrate_photos() -> dict[str, Any]:
    store = get_object_store()
    await store.ensure_bucket()
    moved = orphans = 0
    async for blob in PhotoBlobDocument.find({}):
        meta = await PhotoDocument.find_one({"_id": blob.photo_id})
        if meta is None:
            orphans += 1
        elif not meta.storage_key:
            key = photo_key(meta.tenant_id, meta.id)
            await store.put(key, blob.data, blob.content_type)
            await PhotoDocument.get_motor_collection().update_one(
                {"_id": meta.id}, {"$set": {"storage_key": key}}
            )
            moved += 1
        await PhotoBlobDocument.get_motor_collection().delete_one({"_id": blob.id})
    summary = {"moved": moved, "orphan_blobs_removed": orphans}
    log.info("photos_migrated", **summary)
    return summary


async def _main() -> None:
    await init_database()
    try:
        await migrate_photos()
    finally:
        await close_redis()
        await close_database()


if __name__ == "__main__":
    asyncio.run(_main())
