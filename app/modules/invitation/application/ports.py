"""Cổng của `invitation` — ba nguồn đọc, mỗi nguồn do module sở hữu cắm vào.

Mọi cổng trả dữ liệu THUẦN (dict, list, UUID): `invitation` không import miền của
module nào (§1.2).
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class PublishedWeddings(Protocol):
    """Đám cưới đã xuất bản theo slug -> `(tenant_id, snapshot)` (module `wedding`)."""

    async def by_slug(self, slug: str) -> tuple[UUID, dict[str, Any]] | None: ...


class GuestsByCode(Protocol):
    """Một khách theo mã trong một xưởng (module `guest`)."""

    async def by_code(self, tenant_id: UUID, code: str) -> dict[str, Any] | None: ...


class WordingDefaults(Protocol):
    """Câu chữ mặc định hệ thống: `wording`, `messages` (module `template`)."""

    async def defaults(self) -> dict[str, Any]: ...


class PhotoLister(Protocol):
    """URL ảnh đã ký theo thứ tự album (module `media`)."""

    async def album(self, tenant_id: UUID) -> dict[str, list[str]]:
        """`{"full": [...], "small": [...]}` — cùng thứ tự, phần tử đầu là ảnh bìa."""
        ...


class GuestReplies(Protocol):
    """Nhận phản hồi, đọc lời chúc công khai (module `guest`)."""

    async def respond(
        self, tenant_id: UUID, *, code: str, name: str, status: str, count: int, message: str
    ) -> dict[str, Any]: ...

    async def public_wishes(self, tenant_id: UUID, limit: int) -> list[dict[str, Any]]: ...

    async def record_open(self, tenant_id: UUID, code: str) -> bool: ...

    async def wish(self, tenant_id: UUID, *, name: str, message: str) -> dict[str, Any]: ...


class Entitlements(Protocol):
    """Quyền của gói hiện tại: `per_guest_links`, `remove_badge` (module `billing`)."""

    async def plan_for(self, tenant_id: UUID) -> dict[str, Any]: ...


__all__ = [
    "Entitlements",
    "GuestReplies",
    "GuestsByCode",
    "PhotoLister",
    "PublishedWeddings",
    "WordingDefaults",
]
