"""Hợp đồng lưu trữ của `template`."""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol
from uuid import UUID

from app.modules.template.domain.entities import Intro, Template
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


class IntroRepository(Protocol):
    """Truy cập `intros` (siêu dữ liệu, Mongo) và byte video (kho object S3)."""

    async def list_all(self, *, include_inactive: bool) -> list[Intro]:
        """Theo `order` rồi `created_at` tăng dần."""
        ...

    async def get(self, intro_id: UUID) -> Intro | None: ...

    async def next_order(self) -> int:
        """Thứ tự cho video mới — xếp cuối thư viện."""
        ...

    async def create(
        self, *, name: str, data: bytes, content_type: str, order: int, actor_id: UUID
    ) -> Intro:
        """Ghi byte lên kho rồi mới ghi siêu dữ liệu."""
        ...

    async def update(
        self,
        intro_id: UUID,
        *,
        name: str | None = None,
        is_active: bool | None = None,
        order: int | None = None,
    ) -> Intro | None: ...

    async def delete(self, intro_id: UUID) -> bool:
        """Xoá siêu dữ liệu rồi xoá object trên kho."""
        ...

    async def read_range(self, intro: Intro, start: int, end: int) -> bytes | None:
        """Byte `[start, end]` (gồm cả hai đầu) của video."""
        ...

    def direct_url(self, intro: Intro, expires: timedelta) -> str | None:
        """URL đọc thẳng từ kho (đã ký); None nếu kho không công khai."""
        ...


__all__ = ["IntroRepository", "TemplateRepository"]
