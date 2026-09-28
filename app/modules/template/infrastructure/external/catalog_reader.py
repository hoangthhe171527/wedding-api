"""Cầu nối: tập khoá mẫu hợp lệ — để `wedding` và `guest` kiểm mẫu được gán.

Khớp cấu trúc cổng `TemplateCatalog` mà hai module đó khai.
"""

from __future__ import annotations

from typing import Any

from app.modules.template.infrastructure.persistence.defaults_repository import (
    BeanieCatalogDefaultsRepository,
)
from app.modules.template.infrastructure.persistence.repositories import BeanieTemplateRepository


class TemplateCatalogReader:
    """Đọc khoá mẫu đang có (kể cả mẫu đã tắt — thiệp đã gán vẫn phải hợp lệ)."""

    def __init__(self) -> None:
        self._templates = BeanieTemplateRepository()

    async def known_keys(self) -> frozenset[str]:
        return await self._templates.keys()

    async def tiers(self) -> dict[str, str]:
        """Khoá mẫu -> slug hạng (`free`/`standard`/`premium`) — cho `billing`."""
        return {key: tier.value for key, tier in (await self._templates.tiers()).items()}

    async def names(self) -> dict[str, str]:
        """Khoá mẫu -> tên hiển thị — để câu báo "Mẫu “…” thuộc gói …" đọc được."""
        items = await self._templates.list_all(include_inactive=True)
        return {item.key: item.name for item in items}


class CatalogDefaultsReader:
    """Mặc định hệ thống dạng dữ liệu thuần — cho `wedding` (khởi tạo xưởng) và
    `invitation` (câu chữ mặc định trên web thiệp)."""

    def __init__(self) -> None:
        self._store = BeanieCatalogDefaultsRepository()

    async def defaults(self) -> dict[str, Any]:
        item = await self._store.get()
        return {
            "group_templates": dict(item.group_templates),
            "default_template": item.default_template,
            "wording": {tone: dict(fields) for tone, fields in item.wording.items()},
            "messages": dict(item.messages),
        }


def build_catalog_defaults_reader() -> CatalogDefaultsReader:
    return CatalogDefaultsReader()


def build_template_catalog_reader() -> TemplateCatalogReader:
    """Hàm dựng công bố trên barrel `app.modules.template`."""
    return TemplateCatalogReader()


__all__ = [
    "CatalogDefaultsReader",
    "TemplateCatalogReader",
    "build_catalog_defaults_reader",
    "build_template_catalog_reader",
]
