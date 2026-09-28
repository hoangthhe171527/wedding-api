"""Hợp đồng lưu trữ của `media`."""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol
from uuid import UUID

from app.modules.media.domain.entities import Photo, ProcessedImage


class PhotoRepository(Protocol):
    """Truy cập `photos` (siêu dữ liệu, Mongo) và byte ảnh (kho object S3)."""

    async def list(self, tenant_id: UUID) -> list[Photo]:
        """Ảnh của xưởng theo `order` tăng dần — ảnh đầu là ảnh bìa."""
        ...

    async def get(self, tenant_id: UUID, photo_id: UUID) -> Photo | None: ...

    async def count(self, tenant_id: UUID) -> int: ...

    async def create(
        self, tenant_id: UUID, image: ProcessedImage, *, order: int, actor_id: UUID
    ) -> Photo: ...

    async def set_order(self, tenant_id: UUID, photo_id: UUID, order: int) -> bool: ...

    async def delete(self, tenant_id: UUID, photo_id: UUID) -> bool:
        """Xoá cứng cả siêu dữ liệu lẫn byte ảnh."""
        ...

    async def read_content(
        self, photo_id: UUID, *, small: bool = False
    ) -> tuple[bytes, str] | None:
        """Byte ảnh + content type. Không lọc xưởng: lối vào duy nhất là URL đã ký.

        `small`: bản nhỏ nếu đã có, không thì bản đầy đủ.
        """
        ...

    async def direct_url(
        self, photo_id: UUID, expires: timedelta, *, small: bool = False
    ) -> str | None:
        """URL đọc thẳng từ kho object (đã ký, tự hết hạn); None nếu kho không công khai."""
        ...


__all__ = ["PhotoRepository"]
