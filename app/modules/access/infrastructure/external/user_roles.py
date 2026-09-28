"""Cầu nối: nhãn vai trò theo người dùng, cho màn quản trị tài khoản của `identity`.

Khớp cấu trúc cổng `identity.application.ports.UserRoleReader`.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.access.infrastructure.persistence.repositories import (
    BeanieRoleAssignmentRepository,
    BeanieRoleRepository,
)


class AccessUserRoleReader:
    """Đọc `{user_id: [nhãn vai trò]}` trong hai truy vấn cố định."""

    def __init__(self) -> None:
        self._roles = BeanieRoleRepository()
        self._assignments = BeanieRoleAssignmentRepository()

    async def labels_for(self, user_ids: Sequence[UUID]) -> dict[UUID, list[str]]:
        assignments = await self._assignments.list_for_users(user_ids)
        roles = {
            role.id: role
            for role in await self._roles.find_many(list({item.role_id for item in assignments}))
        }
        out: dict[UUID, list[str]] = {}
        for item in assignments:
            role = roles.get(item.role_id)
            if role is not None:
                out.setdefault(item.user_id, []).append(role.label)
        return out


def build_user_role_reader() -> AccessUserRoleReader:
    """Hàm dựng công bố trên barrel `app.modules.access`."""
    return AccessUserRoleReader()


__all__ = ["AccessUserRoleReader", "build_user_role_reader"]
