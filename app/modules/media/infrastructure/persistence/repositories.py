"""Hiện thực của `PhotoRepository`: siêu dữ liệu ở Mongo, byte ảnh ở kho object.

Ảnh tải lên trước khi có kho object nằm trong `photo_blobs` (không có
`storage_key`); vẫn đọc được cho tới khi chạy `python -m app.seeds.migrate_photos`.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.core.base_model import utc_now
from app.core.logging import get_logger
from app.core.storage import ObjectStore, get_object_store
from app.modules.media.domain.entities import Photo, ProcessedImage
from app.modules.media.infrastructure.persistence.models import PhotoBlobDocument, PhotoDocument

log = get_logger(__name__)


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
        created_at=doc.created_at,
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
        self, tenant_id: UUID, image: ProcessedImage, *, order: int, actor_id: UUID
    ) -> Photo:
        meta = PhotoDocument(
            tenant_id=tenant_id,
            order=order,
            content_type=image.content_type,
            size=len(image.data),
            width=image.width,
            height=image.height,
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
        return _photo(meta)

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
        return True

    async def set_order(self, tenant_id: UUID, photo_id: UUID, order: int) -> bool:
        result = await PhotoDocument.get_motor_collection().update_one(
            {"_id": photo_id, "tenant_id": tenant_id, "deleted_at": None},
            {"$set": {"order": order, "updated_at": utc_now()}},
        )
        return bool(result.matched_count)

    async def delete(self, tenant_id: UUID, photo_id: UUID) -> bool:
        doc = await PhotoDocument.find_one({"_id": photo_id, "tenant_id": tenant_id})
        if doc is None:
            return False
        await PhotoDocument.get_motor_collection().delete_one(
            {"_id": photo_id, "tenant_id": tenant_id}
        )
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

    async def read_content(
        self, photo_id: UUID, *, small: bool = False
    ) -> tuple[bytes, str] | None:
        doc = await PhotoDocument.find_one({"_id": photo_id, "deleted_at": None})
        if doc is None:
            return None
        if doc.storage_key:
            data = await self._store.get(_key(doc, small=small))
            return (data, doc.content_type) if data is not None else None
        blob = await PhotoBlobDocument.find_one({"photo_id": photo_id, "deleted_at": None})
        return (blob.data, blob.content_type) if blob else None

    async def direct_url(
        self, photo_id: UUID, expires: timedelta, *, small: bool = False
    ) -> str | None:
        doc = await PhotoDocument.find_one({"_id": photo_id, "deleted_at": None})
        if doc is None or not doc.storage_key:
            return None
        return self._store.direct_url(_key(doc, small=small), expires)


__all__ = ["SMALL_SUFFIX", "BeaniePhotoRepository", "photo_key"]
