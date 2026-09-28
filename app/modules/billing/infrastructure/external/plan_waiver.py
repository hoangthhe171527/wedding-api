"""Cổng `PlanWaiver` nối sang `access`: xưởng có tài khoản mang quyền
`plan.unlimited` (vai trò quản trị) dùng mọi tính năng không tính phí."""

from __future__ import annotations

from uuid import UUID

from app.core.permissions import Permission
from app.modules.access import build_tenant_permission_reader


class AdminPlanWaiver:
    def __init__(self) -> None:
        self._reader = build_tenant_permission_reader()

    async def waived(self, tenant_id: UUID) -> bool:
        return await self._reader.tenant_has(tenant_id, Permission.PLAN_UNLIMITED.value)


__all__ = ["AdminPlanWaiver"]
