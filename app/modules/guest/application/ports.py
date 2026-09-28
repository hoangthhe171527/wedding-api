"""Cổng của `guest` sang module khác."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class TemplateCatalog(Protocol):
    """Tập khoá mẫu thiệp đang có (module `template`)."""

    async def known_keys(self) -> frozenset[str]: ...


class PlanGuestLimit(Protocol):
    """Hạn mức khách theo gói khi thiệp đang xuất bản (module `wedding` + `billing`).

    `{"limit", "label"}` khi thiệp đang mở; None khi chưa xuất bản (không giới hạn theo gói).
    """

    async def limit_for(self, tenant_id: UUID) -> dict[str, Any] | None: ...


__all__ = ["PlanGuestLimit", "TemplateCatalog"]
