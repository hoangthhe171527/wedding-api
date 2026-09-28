"""Use case: giải tập quyền hiệu lực của một người dùng trong một xưởng.

Gọi mỗi lần đăng nhập, xoay token và `GET /auth/me`. `execute` **không nhận
`ActorContext`** — nó chạy đúng lúc actor chưa tồn tại. Hình dạng tham số khớp
cổng `identity.application.ports.PermissionResolver`, nên `identity` cắm thẳng
vào mà không cần adapter.
"""

from __future__ import annotations

from uuid import UUID

from app.modules.access.domain.repositories import RoleAssignmentRepository, RoleRepository
from app.modules.access.domain.services import merge_permissions


class ResolvePermissions:
    """Hợp nhất quyền của mọi vai trò đang gán cho một người dùng."""

    def __init__(self, roles: RoleRepository, assignments: RoleAssignmentRepository) -> None:
        self._roles = roles
        self._assignments = assignments

    async def execute(self, *, tenant_id: UUID, user_id: UUID) -> frozenset[str]:
        """Tập slug quyền hiệu lực. Không có vai trò nào -> tập rỗng.

        Hai truy vấn cố định bất kể người dùng có bao nhiêu vai trò.
        """
        assignments = await self._assignments.list_for_user(tenant_id, user_id)
        if not assignments:
            return frozenset()
        roles = await self._roles.find_many([item.role_id for item in assignments])
        return merge_permissions(roles)


__all__ = ["ResolvePermissions"]
