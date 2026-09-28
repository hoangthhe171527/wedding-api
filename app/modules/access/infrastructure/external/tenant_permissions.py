"""Cầu nối: một xưởng có ai được gán quyền X không — cho `billing` miễn phí gói.

Hỏi theo SLUG QUYỀN (không theo tên vai trò, ARCHITECTURE §0.1): xưởng của tài
khoản mang quyền `plan.unlimited` (vai trò quản trị) dùng mọi tính năng như gói
cao nhất.
"""

from __future__ import annotations

from uuid import UUID

from app.modules.access.infrastructure.persistence.repositories import (
    BeanieRoleAssignmentRepository,
    BeanieRoleRepository,
)


class TenantPermissionReader:
    def __init__(self) -> None:
        self._roles = BeanieRoleRepository()
        self._assignments = BeanieRoleAssignmentRepository()

    async def tenant_has(self, tenant_id: UUID, permission: str) -> bool:
        assignments = await self._assignments.list_for_tenant(tenant_id)
        if not assignments:
            return False
        roles = await self._roles.find_many(list({item.role_id for item in assignments}))
        return any(permission in role.permissions for role in roles)


def build_tenant_permission_reader() -> TenantPermissionReader:
    """Hàm dựng công bố trên barrel `app.modules.access`."""
    return TenantPermissionReader()


__all__ = ["TenantPermissionReader", "build_tenant_permission_reader"]
