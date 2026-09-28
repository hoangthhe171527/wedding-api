"""Use case: bảo đảm bộ vai trò mặc định tồn tại (idempotent) — gọi khi seed/khởi động."""

from __future__ import annotations

from app.modules.access.domain.entities import Role
from app.modules.access.domain.repositories import RoleRepository
from app.modules.access.domain.role_blueprints import DEFAULT_ROLES


class EnsureDefaultRoles:
    """Tạo vai trò còn thiếu theo `DEFAULT_ROLES`; vai trò đã có được BỔ SUNG quyền
    mới của khuôn (không bao giờ gỡ quyền) — nâng cấp tự áp cho dữ liệu cũ."""

    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    async def execute(self) -> list[Role]:
        return [await self._roles.upsert_blueprint(blueprint) for blueprint in DEFAULT_ROLES]


__all__ = ["EnsureDefaultRoles"]
