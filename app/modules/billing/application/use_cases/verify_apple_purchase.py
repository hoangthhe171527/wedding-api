"""Use case cấp quyền sau khi xác thực giao dịch StoreKit 2."""

from __future__ import annotations

from dataclasses import dataclass

from app.core import audit
from app.core.base_model import utc_now
from app.core.context import ActorContext
from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.modules.billing.application.ports import AppleTransactionVerifier
from app.modules.billing.application.support import current_plan
from app.modules.billing.domain.entities import ApplePurchase, Order
from app.modules.billing.domain.enums import PLAN_RANK, PLAN_SPECS, PaymentMethod, Plan
from app.modules.billing.domain.repositories import (
    ApplePurchaseRepository,
    OrderCodeTakenError,
    OrderRepository,
)
from app.modules.billing.domain.services import generate_order_code, highest_plan

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ApplePurchaseGrant:
    """Kết quả cấp quyền để router trả cho app."""

    transaction_id: str
    plan: Plan
    current_plan: Plan
    activated: bool


class VerifyApplePurchase:
    """Xác thực một transaction và ghi entitlement idempotent cho xưởng."""

    def __init__(
        self,
        orders: OrderRepository,
        purchases: ApplePurchaseRepository,
        verifier: AppleTransactionVerifier,
    ) -> None:
        self._orders = orders
        self._purchases = purchases
        self._verifier = verifier

    async def execute(
        self,
        actor: ActorContext,
        *,
        product_id: str,
        transaction_id: str,
        signed_transaction: str,
    ) -> ApplePurchaseGrant:
        verified = self._verifier.verify(signed_transaction)
        if verified.product_id != product_id or verified.transaction_id != transaction_id:
            raise ConflictError(
                "Thông tin giao dịch không khớp với Apple.",
                code="apple_iap_mismatch",
            )

        purchase = await self._purchases.get_by_transaction_id(verified.transaction_id)
        if purchase is not None and purchase.tenant_id != actor.tenant_id:
            raise ConflictError(
                "Giao dịch Apple đã được gắn với tài khoản khác.",
                code="apple_iap_already_linked",
            )
        if purchase is None:
            purchase = await self._purchases.create(
                transaction_id=verified.transaction_id,
                original_transaction_id=verified.original_transaction_id,
                product_id=verified.product_id,
                plan=verified.plan,
                environment=verified.environment,
                tenant_id=actor.tenant_id,
                purchase_date=verified.purchase_date,
            )

        current = await current_plan(self._orders, actor.tenant_id)
        if PLAN_RANK[current] >= PLAN_RANK[purchase.plan]:
            return ApplePurchaseGrant(
                transaction_id=purchase.transaction_id,
                plan=purchase.plan,
                current_plan=current,
                activated=False,
            )

        order = await self._create_paid_order(actor, purchase)
        log.info(
            "apple_iap_activated",
            tenant_id=str(actor.tenant_id),
            transaction_id=purchase.transaction_id,
            product_id=purchase.product_id,
            plan=purchase.plan.value,
            environment=purchase.environment,
        )
        await audit.record(
            "plan.apple_iap_activated",
            actor_id=actor.user_id,
            target_type="studio",
            target_id=actor.tenant_id,
            tenant_id=actor.tenant_id,
            details={
                "plan": purchase.plan.value,
                "transaction_id": purchase.transaction_id,
                "product_id": purchase.product_id,
                "environment": purchase.environment,
                "order_id": str(order.id),
            },
        )
        return ApplePurchaseGrant(
            transaction_id=purchase.transaction_id,
            plan=purchase.plan,
            current_plan=highest_plan([current, purchase.plan]),
            activated=True,
        )

    async def _create_paid_order(self, actor: ActorContext, purchase: ApplePurchase) -> Order:
        for _ in range(6):
            try:
                order = await self._orders.create(
                    tenant_id=actor.tenant_id,
                    code=generate_order_code(),
                    plan=purchase.plan,
                    amount=PLAN_SPECS[purchase.plan].price,
                    method=PaymentMethod.APPLE_IAP,
                    expires_at=utc_now(),
                    actor_id=actor.user_id,
                )
                break
            except OrderCodeTakenError:
                continue
        else:
            raise ConflictError(
                "Chưa tạo được mã giao dịch. Vui lòng thử lại.",
                code="order_code_exhausted",
            )

        paid = await self._orders.mark_paid(
            order.id,
            reference=f"apple:{purchase.transaction_id}",
            note=f"StoreKit 2 ({purchase.environment}).",
        )
        if paid is None:
            raise ConflictError(
                "Chưa kích hoạt được gói. Vui lòng thử lại.", code="apple_iap_pending"
            )
        return paid


__all__ = ["ApplePurchaseGrant", "VerifyApplePurchase"]
