"""Use case: gói hiện tại, giá nâng cấp và các đơn của xưởng (`GET /billing`)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.context import ActorContext
from app.modules.billing.application.ports import MomoGateway, PlanWaiver
from app.modules.billing.application.support import (
    BankAccountInfo,
    SupportContact,
    bank_account,
    current_plan,
    expire_stale,
    online_payment,
    sandbox,
    support_contact,
)
from app.modules.billing.domain.entities import Order
from app.modules.billing.domain.enums import PLAN_SPECS, Plan
from app.modules.billing.domain.repositories import OrderRepository
from app.modules.billing.domain.services import upgrade_price


@dataclass(frozen=True, slots=True)
class BillingSummary:
    plan: Plan
    #: Gói -> số tiền phải trả để lên gói đó; None = đã có hoặc thấp hơn.
    upgrade_prices: dict[Plan, int | None]
    orders: list[Order]
    bank: BankAccountInfo | None
    momo: bool
    sandbox: bool
    online_payment: bool
    contact: SupportContact


class GetBilling:
    def __init__(
        self, orders: OrderRepository, momo: MomoGateway, waiver: PlanWaiver | None = None
    ) -> None:
        self._orders = orders
        self._momo = momo
        self._waiver = waiver

    async def execute(self, actor: ActorContext) -> BillingSummary:
        await expire_stale(self._orders, actor.tenant_id)
        plan = await current_plan(self._orders, actor.tenant_id, self._waiver)
        return BillingSummary(
            plan=plan,
            upgrade_prices={item: upgrade_price(plan, item) for item in PLAN_SPECS},
            orders=await self._orders.list_for_tenant(actor.tenant_id),
            bank=bank_account(),
            momo=self._momo.enabled,
            sandbox=sandbox(),
            online_payment=online_payment(),
            contact=support_contact(),
        )


__all__ = ["BillingSummary", "GetBilling"]
