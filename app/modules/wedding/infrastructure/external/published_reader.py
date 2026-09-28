"""Cầu nối: đám cưới ĐÃ XUẤT BẢN theo slug — cho web thiệp công khai (`invitation`).

Trả dữ liệu THUẦN `(tenant_id, dict)` chứ không trả thực thể của `wedding`: module
khác không được import miền của nhau (§1.2). Tên trường của dict trùng hợp đồng
HTTP của `GET /wedding`, nên web dùng chung một bộ ánh xạ cho cả hai.

Không bao giờ trả `checklist` (tiến độ nội bộ) hay `published` — phần còn lại
`invitation` tự lọc tiếp (tin nhắn mời, mẫu theo nhóm).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from app.core import cache
from app.modules.wedding.application.support import site_url
from app.modules.wedding.infrastructure.persistence.repositories import (
    PUBLISHED_CACHE,
    BeanieWeddingRepository,
)

#: Bản công khai cũ tối đa chừng này khi slug đổi (khoá cũ không bị xoá chủ động).
PUBLISHED_TTL_SECONDS = 30


class PublishedWeddingReader:
    """Chỉ thấy đám cưới đang bật xuất bản — tắt đi là link công khai trả 404."""

    def __init__(self) -> None:
        self._weddings = BeanieWeddingRepository()

    async def by_slug(self, slug: str) -> tuple[UUID, dict[str, Any]] | None:
        slug = slug.strip().lower()
        # Thiệp nổi (chia sẻ trong nhóm Zalo) bị mở hàng nghìn lần mà nội dung gần như
        # không đổi: giữ bản công khai trên Redis ngắn hạn. Repository xoá khoá này
        # mỗi lần đám cưới được ghi, nên sửa thiệp là khách thấy ngay.
        cached = await cache.get_json(PUBLISHED_CACHE, slug)
        if cached is not None:
            return UUID(cached["tenant_id"]), cached["snapshot"]
        wedding = await self._weddings.find_published_by_slug(slug)
        if wedding is None:
            return None
        snapshot = asdict(wedding.content)
        snapshot["events"] = [
            {**event, "kind": str(event["kind"]), "side": str(event["side"])}
            for event in snapshot["events"]
        ]
        snapshot["open_style"] = str(snapshot["open_style"])
        snapshot["slug"] = wedding.slug
        snapshot["site_url"] = site_url(wedding.slug)
        await cache.set_json(
            {"tenant_id": str(wedding.tenant_id), "snapshot": snapshot},
            PUBLISHED_TTL_SECONDS,
            PUBLISHED_CACHE,
            slug,
        )
        return wedding.tenant_id, snapshot


def build_published_wedding_reader() -> PublishedWeddingReader:
    """Hàm dựng công bố trên barrel `app.modules.wedding`."""
    return PublishedWeddingReader()


__all__ = ["PublishedWeddingReader", "build_published_wedding_reader"]
