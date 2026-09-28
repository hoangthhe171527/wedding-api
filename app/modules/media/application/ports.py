"""Cổng của `media` ra thư viện xử lý ảnh."""

from __future__ import annotations

from typing import Protocol

from app.modules.media.domain.entities import ProcessedImage


class UnreadableImageError(Exception):
    """Tệp không phải ảnh, hoặc ảnh hỏng/quá lớn để giải nén an toàn."""


class ImageProcessor(Protocol):
    """Đọc, xoay đúng chiều, thu nhỏ và mã hoá lại ảnh — bỏ mọi siêu dữ liệu.

    Web thiệp là trang CÔNG KHAI: ảnh chụp bằng điện thoại mang toạ độ GPS trong
    EXIF, tức địa chỉ nhà của cặp đôi. Mã hoá lại từ điểm ảnh là cách chắc chắn
    nhất để không mang theo gì ngoài chính bức ảnh.
    """

    def process(self, data: bytes) -> ProcessedImage:
        """Raises: UnreadableImageError."""
        ...


__all__ = ["ImageProcessor", "UnreadableImageError"]
