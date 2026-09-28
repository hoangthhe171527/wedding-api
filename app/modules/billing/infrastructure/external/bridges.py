"""Cầu nối `billing` công bố cho module khác.

* `wedding` hỏi "đám cưới dùng những thứ này có hợp gói không" (`PlanGate`)
  trước khi xuất bản.
* `invitation` hỏi quyền của gói (`EntitlementReader`) để quyết định có hiện dấu
  "Tạo bởi" và có nhận mã khách trong link hay không.

Chỉ trả dữ liệu thuần (§1.2).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.base_model import utc_now
from app.modules.billing.application.support import current_plan
from app.modules.billing.application.use_cases import CheckPlan
from app.modules.billing.domain.entities import Usage
from app.modules.billing.domain.enums import PLAN_RANK, PLAN_SPECS, PaymentMethod, Plan
from app.modules.billing.domain.services import generate_order_code
from app.modules.billing.infrastructure.external.plan_waiver import AdminPlanWaiver
from app.modules.billing.infrastructure.persistence.repositories import BeanieOrderRepository
from app.modules.template import build_template_catalog_reader


class PlanGate:
    """Xét gói cho một đám cưới."""

    def __init__(self) -> None:
        self._check = CheckPlan(
            BeanieOrderRepository(), build_template_catalog_reader(), AdminPlanWaiver()
        )

    async def check(self, tenant_id: UUID, usage: dict[str, Any]) -> dict[str, Any]:
        """`usage`: `templates`, `open_style`, `guest_count`, `music`, `gift`, `theme`."""
        result = await self._check.execute(
            tenant_id,
            Usage(
                templates=frozenset(str(key) for key in usage.get("templates", ()) if key),
                open_style=str(usage.get("open_style", "")),
                guest_count=int(usage.get("guest_count", 0)),
                music=bool(usage.get("music")),
                gift=bool(usage.get("gift")),
                theme=bool(usage.get("theme")),
                design=bool(usage.get("design")),
            ),
        )
        return {
            "plan": result.plan.value,
            "plan_label": PLAN_SPECS[result.plan].label,
            "required": result.required.value,
            "required_label": PLAN_SPECS[result.required].label,
            "violations": [
                {
                    "code": item.code,
                    "message": item.message,
                    "plan": item.plan.value,
                    "subject": item.subject,
                }
                for item in result.violations
            ],
        }


class EntitlementReader:
    """Quyền của gói hiện tại của một xưởng."""

    def __init__(self) -> None:
        self._orders = BeanieOrderRepository()
        self._waiver = AdminPlanWaiver()

    async def plan_for(self, tenant_id: UUID) -> dict[str, Any]:
        plan = await current_plan(self._orders, tenant_id, self._waiver)
        spec = PLAN_SPECS[plan]
        return {
            "plan": plan.value,
            "label": spec.label,
            "guest_limit": spec.guest_limit,
            "per_guest_links": spec.per_guest_links,
            "remove_badge": spec.remove_badge,
        }


class PlanGranter:
    """Cấp gói không thu tiền — chỉ cho seed tài khoản demo (idempotent).

    Ghi thành một đơn 0đ đã trả, để gói luôn truy ngược được về một đơn.
    """

    def __init__(self) -> None:
        self._orders = BeanieOrderRepository()

    async def grant(self, tenant_id: UUID, plan: str, *, actor_id: UUID, note: str) -> bool:
        """Trả True nếu vừa cấp; False nếu xưởng đã có gói bằng hoặc cao hơn."""
        target = Plan(plan)
        if PLAN_RANK[await current_plan(self._orders, tenant_id)] >= PLAN_RANK[target]:
            return False
        order = await self._orders.create(
            tenant_id=tenant_id,
            code=generate_order_code(),
            plan=target,
            amount=0,
            method=PaymentMethod.BANK_TRANSFER,
            expires_at=utc_now(),
            actor_id=actor_id,
        )
        await self._orders.mark_paid(order.id, reference="grant", note=note)
        return True


def build_plan_gate() -> PlanGate:
    return PlanGate()


def build_entitlement_reader() -> EntitlementReader:
    return EntitlementReader()


def build_plan_granter() -> PlanGranter:
    return PlanGranter()


__all__ = [
    "EntitlementReader",
    "PlanGate",
    "PlanGranter",
    "build_entitlement_reader",
    "build_plan_gate",
    "build_plan_granter",
]
