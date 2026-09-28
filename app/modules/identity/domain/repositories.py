"""Hợp đồng lưu trữ của `identity` — Protocol thuần, không biết Beanie."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.core.pages import Page, PageParams
from app.modules.identity.domain.entities import AuthSession, Studio, User


class StudioRepository(Protocol):
    """Truy cập collection `studios`."""

    async def create(self, *, name: str, studio_id: UUID | None = None) -> Studio:
        """Tạo xưởng mới; `studio_id` cố định chỉ dùng cho seed."""
        ...

    async def find_by_id(self, studio_id: UUID) -> Studio | None: ...

    async def find_many(self, studio_ids: Sequence[UUID]) -> list[Studio]: ...

    async def delete(self, studio_id: UUID) -> None:
        """Xoá cứng — chỉ để hoàn tác một lượt đăng ký dở dang."""
        ...


class UserRepository(Protocol):
    """Truy cập collection `users`."""

    async def find_by_identifier(
        self, *, email: str | None = None, phone: str | None = None
    ) -> User | None:
        """Tìm người dùng theo email hoặc số điện thoại đã chuẩn hoá.

        Ngoại lệ có chủ ý với §0.4 (không lọc tenant): lúc đăng nhập chưa biết
        người này thuộc xưởng nào — và định danh là duy nhất toàn hệ thống.
        """
        ...

    async def find_by_id(self, tenant_id: UUID, user_id: UUID) -> User | None:
        """Lấy người dùng trong phạm vi xưởng. Ngoài phạm vi -> None."""
        ...

    async def find_any_by_id(self, user_id: UUID) -> User | None:
        """Tìm người dùng KHÔNG lọc xưởng — chỉ cho thao tác quản trị hệ thống."""
        ...

    async def create(
        self,
        *,
        tenant_id: UUID,
        full_name: str,
        password_hash: str,
        email: str | None,
        phone: str | None,
        user_id: UUID | None = None,
    ) -> User:
        """Tạo tài khoản; `user_id` cố định chỉ dùng cho seed.

        Raises:
            DuplicateIdentifierError: email/số điện thoại đã có chủ.
        """
        ...

    async def delete(self, user_id: UUID) -> None:
        """Xoá cứng — chỉ để hoàn tác một lượt đăng ký dở dang."""
        ...

    async def set_password_hash(
        self, tenant_id: UUID, user_id: UUID, password_hash: str
    ) -> bool: ...

    async def set_active(self, user_id: UUID, *, is_active: bool, actor_id: UUID) -> bool: ...

    async def touch_login(self, user_id: UUID, at: datetime) -> None: ...

    async def search_all(self, *, query: str | None, params: PageParams) -> Page[User]:
        """Danh sách mọi tài khoản cho đội vận hành (xuyên xưởng, có chủ ý)."""
        ...


class AuthSessionRepository(Protocol):
    """Truy cập collection `auth_sessions`."""

    async def create(
        self,
        *,
        session_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> AuthSession: ...

    async def find_by_refresh_hash(self, refresh_token_hash: str) -> AuthSession | None:
        """Tra phiên theo bản băm, KỂ CẢ phiên đã thu hồi — để phát hiện dùng lại."""
        ...

    async def consume_refresh_hash(
        self, refresh_token_hash: str, now: datetime
    ) -> AuthSession | None:
        """Thu hồi và trả phiên mang bản băm này trong MỘT thao tác nguyên tử.

        Trả None khi không có phiên nào còn sống và chưa hết hạn mang bản băm đó.
        """
        ...

    async def revoke(
        self, tenant_id: UUID, session_id: UUID, *, replaced_by: UUID | None = None
    ) -> bool: ...

    async def revoke_all_for_user(
        self, user_id: UUID, *, except_session_id: UUID | None = None
    ) -> int:
        """Thu hồi mọi phiên còn sống của một người. Trả số phiên bị thu hồi."""
        ...


__all__ = ["AuthSessionRepository", "StudioRepository", "UserRepository"]
