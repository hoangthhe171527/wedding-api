"""Hợp đồng lưu trữ của `wedding`."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.wedding.domain.entities import Wedding, WeddingContent


class SlugTakenError(Exception):
    """Slug đã thuộc đám cưới khác (index duy nhất từ chối)."""


class WeddingAlreadyExistsError(Exception):
    """Xưởng đã có đám cưới (index duy nhất theo tenant từ chối)."""


class WeddingRepository(Protocol):
    """Truy cập collection `weddings`."""

    async def find_by_tenant(self, tenant_id: UUID) -> Wedding | None: ...

    async def find_published_by_slug(self, slug: str) -> Wedding | None:
        """Tra theo slug — ngoại lệ §0.4: link công khai chưa biết tenant."""
        ...

    async def slug_exists(self, slug: str) -> bool: ...

    async def create(
        self, *, tenant_id: UUID, content: WeddingContent, slug: str, actor_id: UUID | None
    ) -> Wedding:
        """Raises: SlugTakenError, WeddingAlreadyExistsError."""
        ...

    async def save_content(
        self, tenant_id: UUID, content: WeddingContent, *, actor_id: UUID
    ) -> Wedding | None: ...

    async def save_checklist(
        self, tenant_id: UUID, checklist: dict[str, bool], *, actor_id: UUID
    ) -> Wedding | None: ...

    async def save_publication(
        self, tenant_id: UUID, *, slug: str, published: bool, actor_id: UUID
    ) -> Wedding | None:
        """Raises: SlugTakenError."""
        ...

    async def list_all(self) -> list[Wedding]:
        """Mọi đám cưới — chỉ cho màn giám sát của đội vận hành (xuyên xưởng)."""
        ...


__all__ = ["SlugTakenError", "WeddingAlreadyExistsError", "WeddingRepository"]
