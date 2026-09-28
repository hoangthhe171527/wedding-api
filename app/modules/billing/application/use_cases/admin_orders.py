"""Use case của đội vận hành: xem đơn, xem sổ báo có, xác nhận đã trả bằng tay."""

from __future__ import annotations

from uuid import UUID

from app.core import audit
from app.core.context import ActorContext
from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.core.pages import Page, PageParams
from app.modules.billing.application.support import expire_stale, order_not_found
from app.modules.billing.domain.entities import Order, PaymentEvent
from app.modules.billing.domain.enums import OrderStatus
from app.modules.billing.domain.repositories import OrderRepository, PaymentEventRepository

log = get_logger(__name__)

_EVENTS_SHOWN = 100


class ListOrders:
    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, params: PageParams, status: OrderStatus | None) -> Page[Order]:
        await expire_stale(self._orders)
        return await self._orders.list_page(params, status)


class ListPaymentEvents:
    def __init__(self, events: PaymentEventRepository) -> None:
        self._events = events

    async def execute(self) -> list[PaymentEvent]:
        return await self._events.list_recent(_EVENTS_SHOWN)


class ConfirmOrder:
    """Đánh dấu đã trả khi tiền về mà hệ thống không tự khớp được.

    Ví dụ: khách ghi sai mã, chuyển thiếu rồi bù, hoặc trả tiền mặt tại quầy
    của studio đối tác. Luôn phải ghi lý do.
    """

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, actor: ActorContext, order_id: UUID, note: str) -> Order:
        """Raises: NotFoundError, ConflictError (đơn đã trả hoặc đã huỷ)."""
        order = await self._orders.get_any(order_id)
        if order is None:
            raise order_not_found()
        paid = await self._orders.mark_paid(
            order_id, reference=f"manual:{actor.user_id}", note=note.strip()
        )
        if paid is None:
            raise ConflictError(
                "Đơn này đã thanh toán hoặc đã huỷ, không xác nhận được.", code="order_not_pending"
            )
        log.info("order_confirmed_manually", code=order.code, by=str(actor.user_id))
        await audit.record(
            "order.confirmed",
            actor_id=actor.user_id,
            target_type="order",
            target_id=order.code,
            tenant_id=order.tenant_id,
            details={"note": note, "plan": order.plan.value, "amount": order.amount},
        )
        return paid


__all__ = ["ConfirmOrder", "ListOrders", "ListPaymentEvents"]
