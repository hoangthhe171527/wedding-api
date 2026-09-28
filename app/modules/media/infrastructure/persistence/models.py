"""Beanie Document của `media` — `photos` (siêu dữ liệu) và `photo_blobs` (cũ).

Byte ảnh nằm ở kho object S3 (`app/core/storage.py`), khoá `storage_key`. Mongo chỉ
giữ siêu dữ liệu. `photo_blobs` là chỗ ảnh từng được lưu trước khi có kho object:
chỉ còn để đọc ảnh chưa chuyển và cho lệnh `python -m app.seeds.migrate_photos`.
"""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from app.core.base_model import ASCENDING, Document, IndexModel, TenantScopedDocument


class PhotoDocument(TenantScopedDocument):
    """Siêu dữ liệu một ảnh cưới."""

    order: int = 0
    content_type: str
    size: int
    width: int
    height: int
    #: Khoá object trong kho S3 (`photos/<xưởng>/<ảnh>`). Rỗng = ảnh cũ còn trong `photo_blobs`.
    storage_key: str = ""
    #: Bản nhỏ cho điện thoại (`<storage_key>.sm`). Rỗng = chưa có, đọc bản đầy đủ.
    small_key: str = ""

    class Settings(TenantScopedDocument.Settings):
        name = "photos"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            IndexModel(
                [("tenant_id", ASCENDING), ("deleted_at", ASCENDING), ("order", ASCENDING)],
                name="ix_photos_tenant_order",
            ),
        ]


class PhotoBlobDocument(TenantScopedDocument):
    """CŨ — byte ảnh từng lưu trong Mongo. Ảnh mới nằm ở kho S3.

    Chỉ còn để đọc ảnh chưa chuyển và cho lệnh `python -m app.seeds.migrate_photos`.
    """

    photo_id: UUID
    content_type: str
    data: bytes

    class Settings(TenantScopedDocument.Settings):
        name = "photo_blobs"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            # Ngoại lệ có chủ ý với §0.4: URL ảnh đã ký chỉ mang `photo_id`.
            IndexModel([("photo_id", ASCENDING)], name="uq_photo_blobs_photo", unique=True),
        ]


DOCUMENTS: list[type[Document]] = [PhotoDocument, PhotoBlobDocument]

__all__ = ["DOCUMENTS", "PhotoBlobDocument", "PhotoDocument"]
