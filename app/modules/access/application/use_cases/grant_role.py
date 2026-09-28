"""Use case: gán một vai trò (theo slug) cho người dùng trong một xưởng.

Dùng ở đường CẤP tài khoản — đăng ký khách dùng mẫu, seed admin. Khớp cổng
`identity.application.ports.RoleGranter`.
"""

from __future__ import annotations

from uuid import UUID

from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger
from app.modules.access.domain.repositories import RoleAssignmentRepository, RoleRepository

log = get_logger(__name__)


class GrantRole:
    """Gán vai trò theo slug; idempotent."""

    def __init__(self, roles: RoleRepository, assignments: RoleAssignmentRepository) -> None:
        self._roles = roles
        self._assignments = assignments

    async def execute(self, *, tenant_id: UUID, user_id: UUID, role_slug: str) -> None:
        """Gán vai trò.

        Raises:
            ServiceUnavailableError: vai trò chưa được khởi tạo. Đây là lỗi cấu
                hình (quên seed), không phải lỗi của người đang đăng ký — nên
                503 chứ không 400, và log để đội vận hành thấy.
        """
        role = await self._roles.find_by_slug(role_slug)
        if role is None:
            log.error("role_blueprint_missing", role_slug=role_slug)
            raise ServiceUnavailableError(
                "Hệ thống chưa sẵn sàng cấp tài khoản. Vui lòng thử lại sau.",
                code="role_not_provisioned",
            )
        await self._assignments.assign(tenant_id, user_id, role.id)


__all__ = ["GrantRole"]
