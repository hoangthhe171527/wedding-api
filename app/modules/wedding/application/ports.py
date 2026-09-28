"""Cổng của `wedding` sang module khác — cắm ở `infrastructure/providers.py`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol
from uuid import UUID


class TemplateCatalog(Protocol):
    """Tập khoá mẫu thiệp đang có (module `template`)."""

    async def known_keys(self) -> frozenset[str]: ...


class CatalogDefaults(Protocol):
    """Mặc định hệ thống: `group_templates`, `default_template` (module `template`)."""

    async def defaults(self) -> dict[str, Any]: ...


class GuestSeeder(Protocol):
    """Nạp danh sách khách mẫu vào một xưởng (module `guest`)."""

    async def seed_sample(self, tenant_id: UUID, *, actor_id: UUID | None) -> int: ...


class GuestCounter(Protocol):
    """Đếm khách theo xưởng cho màn giám sát (module `guest`)."""

    async def count_by_tenant(self, tenant_ids: Sequence[UUID]) -> dict[UUID, int]: ...


class GuestUsage(Protocol):
    """Khách của xưởng đang dùng gì: `count`, `templates`, `groups` (module `guest`)."""

    async def usage(self, tenant_id: UUID) -> dict[str, Any]: ...


class PlanGate(Protocol):
    """Xét những thứ đám cưới đang dùng với gói của xưởng (module `billing`).

    Trả `plan`, `required` (gói thấp nhất đủ dùng) và `violations` (mỗi mục
    `code`, `message`, `plan`).
    """

    async def check(self, tenant_id: UUID, usage: dict[str, Any]) -> dict[str, Any]: ...


class WordingWriter(Protocol):
    """Soạn gợi ý câu chữ thiệp (hiện thực: Claude). `enabled` sai = chưa cấu hình."""

    @property
    def enabled(self) -> bool: ...

    async def suggest(
        self, *, field: str, tone: str, facts: dict[str, str], current: str
    ) -> list[str]:
        """Raises: ServiceUnavailableError, RateLimitedError (lỗi từ nhà cung cấp)."""
        ...


__all__ = [
    "CatalogDefaults",
    "GuestCounter",
    "GuestSeeder",
    "GuestUsage",
    "PlanGate",
    "TemplateCatalog",
    "WordingWriter",
]
