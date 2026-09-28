"""Use case: tạo đơn mua / nâng cấp gói.

Đơn đang chờ trả cùng gói và cùng cách trả thì DÙNG LẠI: khách bấm "Thanh toán"
hai lần không được sinh hai mã chuyển khoản (chuyển theo mã cũ sẽ không khớp).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from app.core.base_model import utc_now
from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.errors import ConflictError, ForbiddenError, ServiceUnavailableError, ValidationError
from app.core.logging import get_logger
from app.modules.billing.application.ports import MomoGateway
from app.modules.billing.application.support import (
    bank_account,
    current_plan,
    online_payment,
    sandbox,
    support_contact,
)
from app.modules.billing.domain.entities import Order
from app.modules.billing.domain.enums import ORDER_TTL_HOURS, PLAN_SPECS, PaymentMethod, Plan
from app.modules.billing.domain.repositories import OrderCodeTakenError, OrderRepository
from app.modules.billing.domain.services import generate_order_code, upgrade_price

log = get_logger(__name__)

_CODE_ATTEMPTS = 6


class CreateOrder:
    def __init__(self, orders: OrderRepository, momo: MomoGateway) -> None:
        self._orders = orders
        self._momo = momo

    async def execute(self, actor: ActorContext, plan: Plan, method: PaymentMethod) -> Order:
        """Raises: ValidationError, ConflictError (đã có gói), ServiceUnavailableError."""
        if not online_payment():
            contact = support_contact()
            raise ForbiddenError(
                f"Nâng gói qua tư vấn: nhắn Zalo {contact.zalo_phone} "
                "để được báo giá và kích hoạt.",
                code="contact_zalo",
            )
        if plan is Plan.FREE:
            raise ValidationError("Gói Miễn phí không cần thanh toán.", code="plan_free")
        current = await current_plan(self._orders, actor.tenant_id)
        amount = upgrade_price(current, plan)
        if amount is None:
            raise ConflictError(
                f"Xưởng đã có {PLAN_SPECS[current].label}, không cần mua {PLAN_SPECS[plan].label}.",
                code="plan_owned",
            )
        self._ensure_method_available(method)

        existing = await self._orders.open_order(actor.tenant_id, plan, method)
        if existing is not None and existing.amount == amount:
            return existing

        order = await self._create(actor, plan, amount, method)
        if method is PaymentMethod.MOMO:
            cfg = get_settings()
            pay_url = await self._momo.create_payment(
                order,
                redirect_url=f"{cfg.PUBLIC_WEB_URL}/billing?order={order.id}",
                ipn_url=f"{cfg.PUBLIC_API_URL}{cfg.API_PREFIX}/billing/webhooks/momo",
            )
            await self._orders.set_pay_url(order.id, pay_url)
            order = replace(order, pay_url=pay_url)
        log.info(
            "order_created",
            tenant_id=str(actor.tenant_id),
            code=order.code,
            plan=plan.value,
            amount=amount,
            method=method.value,
        )
        return order

    def _ensure_method_available(self, method: PaymentMethod) -> None:
        if method is PaymentMethod.BANK_TRANSFER and bank_account() is None and not sandbox():
            raise ServiceUnavailableError(
                "Chưa mở thanh toán chuyển khoản. Vui lòng thử MoMo hoặc liên hệ hỗ trợ.",
                code="bank_unavailable",
            )
        if method is PaymentMethod.MOMO and not self._momo.enabled:
            raise ServiceUnavailableError(
                "Chưa mở thanh toán qua MoMo. Vui lòng chuyển khoản ngân hàng.",
                code="momo_unavailable",
            )

    async def _create(
        self, actor: ActorContext, plan: Plan, amount: int, method: PaymentMethod
    ) -> Order:
        expires_at = utc_now() + timedelta(hours=ORDER_TTL_HOURS)
        for _ in range(_CODE_ATTEMPTS):
            try:
                return await self._orders.create(
                    tenant_id=actor.tenant_id,
                    code=generate_order_code(),
                    plan=plan,
                    amount=amount,
                    method=method,
                    expires_at=expires_at,
                    actor_id=actor.user_id,
                )
            except OrderCodeTakenError:
                continue
        raise ConflictError("Chưa tạo được mã đơn. Vui lòng thử lại.", code="order_code_exhausted")


__all__ = ["CreateOrder"]
