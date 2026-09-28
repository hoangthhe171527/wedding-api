"""Kiểu phân trang THUẦN — dùng được ở tầng domain.

Tách khỏi `app.core.pagination` (nơi có dependency FastAPI và schema Pydantic)
để `domain/repositories.py` khai được `Page[...]` mà không kéo framework vào tầng
domain (ARCHITECTURE §0.2).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any

DEFAULT_PER_PAGE = 20
#: Danh sách khách một đám cưới hiếm khi quá vài trăm thiệp, và màn Khách mời
#: lọc/thống kê trên trọn danh sách — nên trần trang cao hơn mức thông thường.
MAX_PER_PAGE = 500


@dataclass(frozen=True, slots=True)
class PageParams:
    """Tham số phân trang đã chuẩn hoá."""

    page: int = 1
    per_page: int = DEFAULT_PER_PAGE

    @property
    def limit(self) -> int:
        return self.per_page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


@dataclass(frozen=True, slots=True)
class Page[T]:
    """Một trang kết quả trả từ repository lên use case."""

    items: Sequence[T]
    total: int
    params: PageParams

    @property
    def total_pages(self) -> int:
        return ceil(self.total / self.params.per_page) if self.params.per_page else 0

    def meta_dict(self) -> dict[str, Any]:
        return {
            "page": self.params.page,
            "per_page": self.params.per_page,
            "total": self.total,
            "total_pages": self.total_pages,
        }

    def map[U](self, mapper: Callable[[T], U]) -> Page[U]:
        """Chuyển từng phần tử sang kiểu khác, giữ nguyên thông tin trang."""
        return Page(
            items=[mapper(item) for item in self.items], total=self.total, params=self.params
        )


__all__ = ["DEFAULT_PER_PAGE", "MAX_PER_PAGE", "Page", "PageParams"]
