"""Hợp đồng lưu trữ của `access` — Protocol thuần, không biết Beanie."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.access.domain.entities import Role, RoleAssignment
from app.modules.access.domain.role_blueprints import RoleBlueprint


class RoleRepository(Protocol):
    """Truy cập collection `roles`."""

    async def list_all(self) -> list[Role]:
        """Mọi vai trò, theo thứ tự tạo."""
        ...

    async def find_by_slug(self, slug: str) -> Role | None:
        """Vai trò theo slug."""
        ...

    async def find_many(self, role_ids: Sequence[UUID]) -> list[Role]:
        """Nhiều vai trò theo id — một truy vấn, không N+1."""
        ...

    async def upsert_blueprint(self, blueprint: RoleBlueprint) -> Role:
        """Tạo vai trò theo khuôn nếu chưa có; có rồi thì giữ nguyên (idempotent)."""
        ...


class RoleAssignmentRepository(Protocol):
    """Truy cập collection `role_assignments`."""

    async def list_for_user(self, tenant_id: UUID, user_id: UUID) -> list[RoleAssignment]:
        """Vai trò của một người trong một xưởng."""
        ...

    async def list_for_users(self, user_ids: Sequence[UUID]) -> list[RoleAssignment]:
        """Vai trò của nhiều người, KHÔNG lọc xưởng.

        Ngoại lệ có chủ ý (ARCHITECTURE §0.4): chỉ màn quản trị tài khoản của đội
        vận hành gọi — danh sách id luôn do phía gọi lấy từ đúng câu truy vấn mà
        quyền `user.manage` đã cho phép.
        """
        ...

    async def assign(self, tenant_id: UUID, user_id: UUID, role_id: UUID) -> RoleAssignment:
        """Gán vai trò; gán lại vai trò đã có là thao tác rỗng."""
        ...


__all__ = ["RoleAssignmentRepository", "RoleRepository"]
