"""Use case: danh sách vai trò (màn quản trị tài khoản)."""

from __future__ import annotations

from app.modules.access.domain.entities import Role
from app.modules.access.domain.repositories import RoleRepository


class ListRoles:
    """Mọi vai trò của hệ thống cùng tập quyền."""

    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    async def execute(self) -> list[Role]:
        return await self._roles.list_all()


__all__ = ["ListRoles"]
