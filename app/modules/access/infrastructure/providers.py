"""Lắp ráp phụ thuộc của `access`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.access.application.use_cases import (
    EnsureDefaultRoles,
    GrantRole,
    ListRoles,
    ResolvePermissions,
)
from app.modules.access.infrastructure.persistence.repositories import (
    BeanieRoleAssignmentRepository,
    BeanieRoleRepository,
)


def build_resolve_permissions() -> ResolvePermissions:
    """Use case giải quyền — `identity` cắm vào cổng `PermissionResolver`."""
    return ResolvePermissions(BeanieRoleRepository(), BeanieRoleAssignmentRepository())


def build_grant_role() -> GrantRole:
    """Use case gán vai trò — `identity` cắm vào cổng `RoleGranter`."""
    return GrantRole(BeanieRoleRepository(), BeanieRoleAssignmentRepository())


def build_ensure_default_roles() -> EnsureDefaultRoles:
    """Use case seed vai trò mặc định."""
    return EnsureDefaultRoles(BeanieRoleRepository())


def provide_list_roles() -> ListRoles:
    return ListRoles(BeanieRoleRepository())


ListRolesDep = Annotated[ListRoles, Depends(provide_list_roles)]

__all__ = [
    "ListRolesDep",
    "build_ensure_default_roles",
    "build_grant_role",
    "build_resolve_permissions",
]
