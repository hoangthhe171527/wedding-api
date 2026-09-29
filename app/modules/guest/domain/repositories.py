"""Hợp đồng lưu trữ của `guest`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.core.pages import Page, PageParams
from app.modules.guest.domain.entities import Guest, GuestDraft, InviteLink, Wish
from app.modules.guest.domain.enums import RsvpStatus


class GuestCodeTakenError(Exception):
    """Mã khách đã có trong xưởng (index duy nhất từ chối) — sinh mã khác rồi thử lại."""


class GuestRepository(Protocol):
    """Truy cập collection `guests`."""

    async def list_page(self, tenant_id: UUID, params: PageParams) -> Page[Guest]:
        """Khách của một xưởng theo thứ tự thêm vào (thiệp cũ trước, như thiết kế)."""
        ...

    async def get(self, tenant_id: UUID, guest_id: UUID) -> Guest | None: ...

    async def find_by_code(self, tenant_id: UUID, code: str) -> Guest | None: ...

    async def count(self, tenant_id: UUID) -> int: ...

    async def count_by_tenant(self, tenant_ids: Sequence[UUID]) -> dict[UUID, int]: ...

    async def usage(self, tenant_id: UUID) -> tuple[int, frozenset[str], frozenset[str]]:
        """(số thiệp, mẫu riêng đang gán, nhóm khách đang có) của một xưởng."""
        ...

    async def create(
        self, tenant_id: UUID, code: str, draft: GuestDraft, *, actor_id: UUID | None
    ) -> Guest:
        """Raises: GuestCodeTakenError."""
        ...

    async def replace(
        self, tenant_id: UUID, guest_id: UUID, draft: GuestDraft, *, actor_id: UUID
    ) -> Guest | None: ...

    async def create_many(
        self,
        tenant_id: UUID,
        items: Sequence[tuple[str, GuestDraft]],
        *,
        actor_id: UUID | None,
    ) -> tuple[list[Guest], list[int]]:
        """Tạo hàng loạt một lượt; trả (khách đã tạo, vị trí bị trùng mã cần thử lại)."""
        ...

    async def discard(self, tenant_id: UUID, guest_ids: Sequence[UUID]) -> None:
        """Xoá hẳn — chỉ để hoàn tác khách vừa tạo khi vượt hạn mức."""
        ...

    async def soft_delete(self, tenant_id: UUID, guest_id: UUID, *, actor_id: UUID) -> bool: ...

    async def record_reply(
        self, tenant_id: UUID, code: str, *, status: RsvpStatus, count: int, message: str
    ) -> Guest | None:
        """Ghi phản hồi khách tự gửi: đổi `status` + lưu số người, lời nhắn, thời điểm."""
        ...

    async def record_open(self, tenant_id: UUID, code: str) -> bool:
        """Khách mở link riêng: tăng số lần mở, giữ lần đầu, ghi lần gần nhất."""
        ...


class WishRepository(Protocol):
    """Truy cập collection `guest_wishes`."""

    async def add(
        self,
        tenant_id: UUID,
        *,
        name: str,
        message: str,
        status: RsvpStatus,
        count: int,
        guest_code: str,
        link: str = "",
    ) -> Wish: ...

    async def list_recent(self, tenant_id: UUID, *, limit: int, with_message: bool) -> list[Wish]:
        """Mới nhất trước. `with_message` = chỉ lấy dòng có lời chúc (web công khai)."""
        ...

    async def soft_delete(self, tenant_id: UUID, wish_id: UUID, *, actor_id: UUID) -> bool: ...


class LinkSlugTakenError(Exception):
    """Đuôi link đã có trong xưởng (index duy nhất từ chối)."""


class InviteLinkRepository(Protocol):
    """Truy cập collection `guest_links`."""

    async def list_all(self, tenant_id: UUID) -> list[InviteLink]:
        """Link của một xưởng theo thứ tự tạo."""
        ...

    async def get(self, tenant_id: UUID, link_id: UUID) -> InviteLink | None: ...

    async def find_by_slug(self, tenant_id: UUID, slug: str) -> InviteLink | None: ...

    async def count(self, tenant_id: UUID) -> int: ...

    async def templates(self, tenant_id: UUID) -> frozenset[str]:
        """Mẫu riêng các link đang gán — tính vào mẫu đang dùng khi xét gói."""
        ...

    async def create(
        self, tenant_id: UUID, *, slug: str, name: str, template: str, actor_id: UUID
    ) -> InviteLink:
        """Raises: LinkSlugTakenError."""
        ...

    async def update(
        self,
        tenant_id: UUID,
        link_id: UUID,
        *,
        slug: str,
        name: str,
        template: str,
        actor_id: UUID,
    ) -> InviteLink | None:
        """Raises: LinkSlugTakenError."""
        ...

    async def soft_delete(self, tenant_id: UUID, link_id: UUID, *, actor_id: UUID) -> bool:
        """Xoá mềm VÀ nhả đuôi link để tạo lại được link cùng tên."""
        ...

    async def record_open(self, tenant_id: UUID, slug: str) -> bool: ...


__all__ = [
    "GuestCodeTakenError",
    "GuestRepository",
    "InviteLinkRepository",
    "LinkSlugTakenError",
    "WishRepository",
]
