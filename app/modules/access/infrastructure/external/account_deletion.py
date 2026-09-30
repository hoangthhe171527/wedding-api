"""Xoá gán quyền khi một xưởng yêu cầu xoá tài khoản."""

from __future__ import annotations

from uuid import UUID

from app.modules.access.infrastructure.persistence.models import RoleAssignmentDocument


class AccountDataDeleter:
    async def execute(self, tenant_id: UUID) -> None:
        await RoleAssignmentDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})


def build_account_data_deleter() -> AccountDataDeleter:
    return AccountDataDeleter()


__all__ = ["AccountDataDeleter", "build_account_data_deleter"]
