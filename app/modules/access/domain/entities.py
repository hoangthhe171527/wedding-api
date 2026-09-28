"""Thực thể thuần của `access`."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Role:
    """Một vai trò: tên gọi cho một tập slug quyền.

    Vai trò ở hệ này là **toàn hệ thống**, không theo xưởng: mọi xưởng dùng cùng
    bộ `admin` / `customer`. Tập quyền vẫn là dữ liệu — đổi quyền của một vai trò
    là sửa một hàng, không sửa mã.
    """

    id: UUID
    slug: str
    label: str
    permissions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    """Người dùng `user_id` giữ vai trò `role_id` trong xưởng `tenant_id`."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    role_id: UUID


__all__ = ["Role", "RoleAssignment"]
