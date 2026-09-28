"""Thực thể thuần của `media`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

#: Định dạng lưu sau khi chuẩn hoá — trình duyệt nào cũng hiển thị được.
STORED_TYPES: Final[frozenset[str]] = frozenset({"image/jpeg", "image/png"})


@dataclass(frozen=True, slots=True)
class Photo:
    """Siêu dữ liệu một ảnh cưới (byte ảnh nằm riêng, không tải kèm danh sách).

    Attributes:
        order: Thứ tự trong album; ảnh có `order` nhỏ nhất là ẢNH BÌA.
    """

    id: UUID
    tenant_id: UUID
    order: int
    content_type: str
    size: int
    width: int
    height: int
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    """Ảnh đã chuẩn hoá: xoay đúng chiều, thu nhỏ, bỏ EXIF."""

    data: bytes
    content_type: str
    width: int
    height: int
    #: Bản nhỏ (ngang `SMALL_WIDTH`) cho điện thoại; None khi ảnh gốc đã đủ nhỏ.
    small: bytes | None = None


__all__ = ["STORED_TYPES", "Photo", "ProcessedImage"]
