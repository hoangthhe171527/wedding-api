"""Hiện thực của `PhotoRepository`: siêu dữ liệu ở Mongo, byte ảnh ở kho object.

Ảnh tải lên trước khi có kho object nằm trong `photo_blobs` (không có
`storage_key`); vẫn đọc được cho tới khi chạy `python -m app.seeds.migrate_photos`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import UUID

from app.core import cache
from app.core.base_model import utc_now
from app.core.logging import get_logger
from app.core.storage import ObjectStore, get_object_store
from app.modules.media.domain.entities import ADJUST_FIELDS, Photo, PhotoAdjust, ProcessedImage
from app.modules.media.infrastructure.persistence.models import PhotoBlobDocument, PhotoDocument

log = get_logger(__name__)

PHOTO_META_CACHE = "photo_meta"
PUBLIC_ALBUM_CACHE = "public_album"
_PHOTO_META_TTL = 3600


async def invalidate_photo_cache(tenant_id: UUID, photo_id: UUID | None = None) -> None:
    """Xoá cache album công khai (theo xưởng) và metadata ảnh (nếu truyền `photo_id`)."""
    await cache.delete(PUBLIC_ALBUM_CACHE, str(tenant_id))
    if photo_id is not None:
        await cache.delete(PHOTO_META_CACHE, str(photo_id))


def photo_key(tenant_id: UUID, photo_id: UUID) -> str:
    """Khoá object: gom theo xưởng để xoá / sao lưu / tính dung lượng theo xưởng."""
    return f"photos/{tenant_id}/{photo_id}"


#: Hậu tố khoá object của bản nhỏ.
SMALL_SUFFIX = ".sm"


def _key(doc: PhotoDocument, *, small: bool) -> str:
    """Bản nhỏ nếu được hỏi VÀ đã có; không thì bản đầy đủ (ảnh cũ chưa chạy bù)."""
    return doc.small_key if small and doc.small_key else doc.storage_key


def _photo(doc: PhotoDocument) -> Photo:
    return Photo(
        id=doc.id,
        tenant_id=doc.tenant_id,
        order=doc.order,
        content_type=doc.content_type,
        size=doc.size,
        width=doc.width,
        height=doc.height,
        content_hash=doc.content_hash,
        focus_x=doc.focus_x,
        focus_y=doc.focus_y,
        adjust=PhotoAdjust(**{name: getattr(doc, name) for name in ADJUST_FIELDS}),
        created_at=doc.created_at,
        storage_key=doc.storage_key,
        small_key=doc.small_key,
    )


class BeaniePhotoRepository:
    """`PhotoRepository` trên Mongo + kho object S3."""

    def __init__(self, store: ObjectStore | None = None) -> None:
        self._store = store or get_object_store()

    async def list(self, tenant_id: UUID) -> list[Photo]:
        docs = await PhotoDocument.scoped(tenant_id).sort("+order", "+created_at").to_list()
        return [_photo(doc) for doc in docs]

    async def get(self, tenant_id: UUID, photo_id: UUID) -> Photo | None:
        doc = await PhotoDocument.get_scoped(tenant_id, photo_id)
        return _photo(doc) if doc else None

    async def count(self, tenant_id: UUID) -> int:
        return int(await PhotoDocument.scoped(tenant_id).count())

    async def create(
        self,
        tenant_id: UUID,
        image: ProcessedImage,
        *,
        order: int,
        actor_id: UUID,
        content_hash: str,
        adjust: PhotoAdjust | None = None,
    ) -> Photo:
        meta = PhotoDocument(
            tenant_id=tenant_id,
            order=order,
            content_type=image.content_type,
            size=len(image.data),
            width=image.width,
            height=image.height,
            content_hash=content_hash,
            **asdict(adjust or PhotoAdjust()),
        ).stamp_created(actor_id)
        meta.storage_key = photo_key(tenant_id, meta.id)
        # Byte trước, siêu dữ liệu sau: album không bao giờ trỏ vào ảnh chưa có.
        # Ghi siêu dữ liệu hỏng thì dọn object vừa ghi để không mồ côi.
        await self._store.put(meta.storage_key, image.data, image.content_type)
        try:
            if image.small is not None:
                small_key = f"{meta.storage_key}{SMALL_SUFFIX}"
                await self._store.put(small_key, image.small, image.content_type)
                meta.small_key = small_key
            await meta.insert()
        except Exception:
            await self._store.delete(meta.storage_key)
            if meta.small_key:
                await self._store.delete(meta.small_key)
            raise
        await invalidate_photo_cache(tenant_id)
        return _photo(meta)

    async def find_by_hash(
        self, tenant_id: UUID, content_hash: str, *, excluding: UUID | None = None
    ) -> Photo | None:
        """Tìm ảnh trùng; đồng thời bù hash cho ảnh cũ chưa có trường này."""
        query: dict[str, object] = {
            "tenant_id": tenant_id,
            "deleted_at": None,
            "content_hash": content_hash,
        }
        if excluding is not None:
            query["_id"] = {"$ne": excluding}
        found = await PhotoDocument.find_one(query)
        if found is not None:
            return _photo(found)

        legacy = await PhotoDocument.find(
            {
                "tenant_id": tenant_id,
                "deleted_at": None,
                "$or": [{"content_hash": ""}, {"content_hash": None}],
            }
        ).to_list()
        for doc in legacy:
            content = await self.read_content(doc.id)
            if content is None:
                continue
            digest = hashlib.sha256(content[0]).hexdigest()
            await PhotoDocument.get_motor_collection().update_one(
                {"_id": doc.id, "tenant_id": tenant_id}, {"$set": {"content_hash": digest}}
            )
            if digest == content_hash and doc.id != excluding:
                doc.content_hash = digest
                return _photo(doc)
        return None

    async def attach_small(self, photo_id: UUID, data: bytes) -> bool:
        """Gắn bản nhỏ cho ảnh cũ (chạy bù). False nếu ảnh không còn / chưa lên kho."""
        doc = await PhotoDocument.find_one({"_id": photo_id, "deleted_at": None})
        if doc is None or not doc.storage_key:
            return False
        small_key = f"{doc.storage_key}{SMALL_SUFFIX}"
        await self._store.put(small_key, data, doc.content_type)
        await PhotoDocument.get_motor_collection().update_one(
            {"_id": photo_id}, {"$set": {"small_key": small_key}}
        )
        await invalidate_photo_cache(doc.tenant_id, photo_id)
        return True

    async def set_order(self, tenant_id: UUID, photo_id: UUID, order: int) -> bool:
        result = await PhotoDocument.get_motor_collection().update_one(
            {"_id": photo_id, "tenant_id": tenant_id, "deleted_at": None},
            {"$set": {"order": order, "updated_at": utc_now()}},
        )
        updated = bool(result.matched_count)
        if updated:
            await invalidate_photo_cache(tenant_id)
        return updated

    async def set_focus(
        self, tenant_id: UUID, photo_id: UUID, focus_x: float, focus_y: float
    ) -> bool:
        result = await PhotoDocument.get_motor_collection().update_one(
            {"_id": photo_id, "tenant_id": tenant_id, "deleted_at": None},
            {
                "$set": {
                    "focus_x": focus_x,
                    "focus_y": focus_y,
                    "updated_at": utc_now(),
                }
            },
        )
        updated = bool(result.matched_count)
        if updated:
            await invalidate_photo_cache(tenant_id)
        return updated

    async def set_adjust(self, tenant_id: UUID, photo_id: UUID, fields: Mapping[str, Any]) -> bool:
        result = await PhotoDocument.get_motor_collection().update_one(
            {"_id": photo_id, "tenant_id": tenant_id, "deleted_at": None},
            {"$set": {**fields, "updated_at": utc_now()}},
        )
        updated = bool(result.matched_count)
        if updated:
            await invalidate_photo_cache(tenant_id)
        return updated

    async def delete(self, tenant_id: UUID, photo_id: UUID) -> bool:
        doc = await PhotoDocument.find_one({"_id": photo_id, "tenant_id": tenant_id})
        if doc is None:
            return False
        await PhotoDocument.get_motor_collection().delete_one(
            {"_id": photo_id, "tenant_id": tenant_id}
        )
        await invalidate_photo_cache(tenant_id, photo_id)
        # Siêu dữ liệu đã xoá thì ảnh không còn hiện ở đâu; object còn sót (kho
        # lỗi tạm thời) chỉ tốn chỗ, không lộ gì — ghi log để dọn sau.
        try:
            if doc.small_key:
                await self._store.delete(doc.small_key)
            if doc.storage_key:
                await self._store.delete(doc.storage_key)
            else:
                await PhotoBlobDocument.get_motor_collection().delete_one(
                    {"photo_id": photo_id, "tenant_id": tenant_id}
                )
        except Exception:
            log.warning("photo_object_orphaned", photo_id=str(photo_id), key=doc.storage_key)
        return True

    async def _load_meta(self, photo_id: UUID) -> tuple[str, str, str] | None:
        cached = await cache.get_json(PHOTO_META_CACHE, str(photo_id))
        if isinstance(cached, dict) and cached.get("storage_key"):
            return (
                str(cached["storage_key"]),
                str(cached.get("small_key") or ""),
                str(cached.get("content_type") or ""),
            )
        doc = await PhotoDocument.find_one({"_id": photo_id, "deleted_at": None})
        if doc is None:
            return None
        if doc.storage_key:
            await cache.set_json(
                {
                    "storage_key": doc.storage_key,
                    "small_key": doc.small_key,
                    "content_type": doc.content_type,
                },
                _PHOTO_META_TTL,
                PHOTO_META_CACHE,
                str(photo_id),
            )
        return doc.storage_key, doc.small_key, doc.content_type

    async def read_content(
        self, photo_id: UUID, *, small: bool = False
    ) -> tuple[bytes, str] | None:
        meta = await self._load_meta(photo_id)
        if meta is None:
            return None
        storage_key, small_key, content_type = meta
        if storage_key:
            key = small_key if small and small_key else storage_key
            data = await self._store.get(key)
            return (data, content_type) if data is not None else None
        blob = await PhotoBlobDocument.find_one({"photo_id": photo_id, "deleted_at": None})
        return (blob.data, blob.content_type) if blob else None

    async def direct_url(
        self, photo_id: UUID, expires: timedelta, *, small: bool = False
    ) -> str | None:
        meta = await self._load_meta(photo_id)
        if meta is None or not meta[0]:
            return None
        storage_key, small_key, _ = meta
        key = small_key if small and small_key else storage_key
        return self._store.direct_url(key, expires)


__all__ = [
    "PHOTO_META_CACHE",
    "PUBLIC_ALBUM_CACHE",
    "SMALL_SUFFIX",
    "BeaniePhotoRepository",
    "invalidate_photo_cache",
    "photo_key",
]
