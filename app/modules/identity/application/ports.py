"""Cổng của `identity` sang thế giới bên ngoài module.

`identity` phát hành token, mà token phải chứa tập quyền — thứ do module `access`
sở hữu. Thay vì import thẳng use case của `access`, `identity` khai cổng dưới
đây; `infrastructure/providers.py` là nơi DUY NHẤT biết ai cắm vào. Nhờ vậy test
đăng nhập chạy được với resolver giả, không cần dựng vai trò.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID


class PermissionResolver(Protocol):
    """Giải tập quyền hiệu lực của một người dùng trong một xưởng."""

    async def execute(self, *, tenant_id: UUID, user_id: UUID) -> frozenset[str]: ...


class RoleGranter(Protocol):
    """Gán vai trò theo slug — dùng ở đường cấp tài khoản."""

    async def execute(self, *, tenant_id: UUID, user_id: UUID, role_slug: str) -> None: ...


class UserRoleReader(Protocol):
    """Nhãn vai trò theo người dùng — cho màn quản trị tài khoản."""

    async def labels_for(self, user_ids: Sequence[UUID]) -> dict[UUID, list[str]]: ...


class TenantDataDeleter(Protocol):
    """Xoá dữ liệu do một module sở hữu trong một xưởng."""

    async def execute(self, tenant_id: UUID) -> None: ...


__all__ = ["PermissionResolver", "RoleGranter", "TenantDataDeleter", "UserRoleReader"]
