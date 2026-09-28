"""Cổng của `template` — hợp đồng lưu trữ dùng ở use case."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.template.domain.defaults import CatalogDefaults


class DefaultsStore(Protocol):
    """Đọc / ghi mặc định hệ thống (`catalog_defaults`)."""

    async def get(self) -> CatalogDefaults: ...

    async def save(self, defaults: CatalogDefaults, *, actor_id: UUID) -> CatalogDefaults: ...


class TemplateKeys(Protocol):
    """Tập khoá mẫu đang có."""

    async def keys(self) -> frozenset[str]: ...


__all__ = ["DefaultsStore", "TemplateKeys"]
