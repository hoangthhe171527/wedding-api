"""Hợp đồng lưu trữ của `template`."""

from __future__ import annotations

from typing import Protocol

from app.modules.template.domain.entities import Template
from app.modules.template.domain.enums import Tier


class TemplateRepository(Protocol):
    """Truy cập collection `templates`."""

    async def list_all(self, *, include_inactive: bool) -> list[Template]:
        """Mọi mẫu theo `sort_order`."""
        ...

    async def find(self, key: str) -> Template | None: ...

    async def keys(self) -> frozenset[str]:
        """Mọi khoá mẫu đang có (kể cả mẫu đã tắt)."""
        ...

    async def insert_missing(self, blueprints: tuple[Template, ...]) -> int:
        """Tạo mẫu chưa có; KHÔNG đè mẫu đã có. Trả số mẫu vừa tạo."""
        ...

    async def backfill_tiers(self, blueprints: tuple[Template, ...]) -> int:
        """Gắn hạng cho mẫu cũ chưa có trường hạng. Trả số mẫu vừa gắn."""
        ...

    async def retire(self, keys: frozenset[str]) -> int:
        """Tắt MỘT lần các mẫu cho nghỉ; mẫu đã xử lý thì bỏ qua. Trả số mẫu vừa tắt."""
        ...

    async def tiers(self) -> dict[str, Tier]: ...

    async def update_flags(
        self,
        key: str,
        *,
        is_active: bool | None = None,
        is_new: bool | None = None,
        sort_order: int | None = None,
        tier: Tier | None = None,
    ) -> Template | None: ...


__all__ = ["TemplateRepository"]
