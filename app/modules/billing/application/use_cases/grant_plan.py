"""Use case của đội vận hành: cấp gói cho một xưởng (khách liên hệ qua Zalo).

Nâng gói hiện đi qua tư vấn: khách nhắn Zalo, đội vận hành chốt giá rồi cấp gói
ở màn quản trị. Mỗi lần cấp ghi thành một đơn ĐÃ TRẢ kèm số tiền đã thu (có thể
0) và ghi chú — gói luôn truy ngược được về một dòng đơn để đối soát.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core import audit
from app.core.base_model import utc_now
from app.core.context import ActorContext
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.modules.billing.application.support import current_plan
from app.modules.billing.domain.entities import Order
from app.modules.billing.domain.enums import PLAN_RANK, PLAN_SPECS, PaymentMethod, Plan
from app.modules.billing.domain.repositories import OrderCodeTakenError, OrderRepository
from app.modules.billing.domain.services import generate_order_code, highest_plan

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PlanGrant:
    plan: Plan
    amount: int
    note: str


class StudioDirectory(Protocol):
    """Xưởng có tồn tại không (module `identity`)."""

    async def exists(self, studio_id: UUID) -> bool: ...


class GrantPlan:
    def __init__(self, orders: OrderRepository, studios: StudioDirectory | None = None) -> None:
        self._orders = orders
        self._studios = studios

    async def execute(self, actor: ActorContext, studio_id: UUID, grant: PlanGrant) -> Order:
        """Raises: ValidationError (gói Miễn phí, thiếu ghi chú), ConflictError (đã có gói)."""
        if grant.plan is Plan.FREE:
            raise ValidationError("Không cần cấp gói Miễn phí.", code="plan_free")
        if len(grant.note.strip()) < 3:
            raise ValidationError(
                "Ghi chú cách khách đã trả (vd: “CK Vietcombank 12/10, Zalo chị Lan”).",
                code="grant_note",
                errors={"note": ["Nhập ghi chú."]},
            )
        if self._studios is not None and not await self._studios.exists(studio_id):
            # Id gõ nhầm: không được ghi một đơn "đã trả" cho xưởng không tồn tại.
            raise NotFoundError("Không tìm thấy xưởng thiệp.", code="studio_not_found")
        current = await current_plan(self._orders, studio_id)
        if PLAN_RANK[current] >= PLAN_RANK[grant.plan]:
            raise ConflictError(f"Xưởng đã có {PLAN_SPECS[current].label}.", code="plan_owned")
        for _ in range(6):
            try:
                order = await self._orders.create(
                    tenant_id=studio_id,
                    code=generate_order_code(),
                    plan=grant.plan,
                    amount=max(grant.amount, 0),
                    method=PaymentMethod.BANK_TRANSFER,
                    expires_at=utc_now(),
                    actor_id=actor.user_id,
                )
                break
            except OrderCodeTakenError:
                continue
        else:
            raise ConflictError("Chưa tạo được mã đơn. Thử lại.", code="order_code_exhausted")
        paid = await self._orders.mark_paid(
            order.id, reference=f"manual:{actor.user_id}", note=grant.note.strip()
        )
        log.info(
            "plan_granted",
            studio_id=str(studio_id),
            plan=grant.plan.value,
            amount=grant.amount,
            by=str(actor.user_id),
        )
        result = paid or order
        await audit.record(
            "plan.granted",
            actor_id=actor.user_id,
            target_type="studio",
            target_id=studio_id,
            tenant_id=studio_id,
            details={"plan": grant.plan.value, "amount": grant.amount, "note": grant.note},
        )
        return result


class StudioPlans:
    """Gói hiện tại của nhiều xưởng — cột "Gói" ở màn quản trị tài khoản."""

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, studio_ids: list[UUID]) -> dict[UUID, Plan]:
        # Một aggregate cho cả trang thay vì một truy vấn cho mỗi xưởng (N+1).
        paid = await self._orders.paid_plans_many(studio_ids)
        return {studio_id: highest_plan(plans) for studio_id, plans in paid.items()}


__all__ = ["GrantPlan", "PlanGrant", "StudioPlans"]
