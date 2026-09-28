"""Use case: đám cưới đang dùng những gì vượt gói hiện tại.

`wedding` gọi trước khi xuất bản (qua cầu nối) và web gọi để hiện "cần nâng
gói" ở tab Xuất bản. `billing` không đọc dữ liệu đám cưới: `wedding` gom
`Usage` và gửi sang, nên hai module không phụ thuộc vòng.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.billing.application.ports import TemplateCatalog
from app.modules.billing.application.support import current_plan
from app.modules.billing.domain.entities import Usage, Violation
from app.modules.billing.domain.enums import Plan
from app.modules.billing.domain.repositories import OrderRepository
from app.modules.billing.domain.services import required_plan, violations


@dataclass(frozen=True, slots=True)
class PlanCheck:
    plan: Plan
    required: Plan
    violations: list[Violation]


class CheckPlan:
    def __init__(self, orders: OrderRepository, templates: TemplateCatalog) -> None:
        self._orders = orders
        self._templates = templates

    async def execute(self, tenant_id: UUID, usage: Usage) -> PlanCheck:
        plan = await current_plan(self._orders, tenant_id)
        found = violations(
            plan, usage, await self._templates.tiers(), await self._templates.names()
        )
        return PlanCheck(plan=plan, required=required_plan(found, plan), violations=found)


__all__ = ["CheckPlan", "PlanCheck"]
