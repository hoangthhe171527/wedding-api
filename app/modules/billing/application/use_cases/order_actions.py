"""Use case trên một đơn của xưởng: xem, huỷ, giả lập đã trả (chỉ local/test)."""

from __future__ import annotations

from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import ConflictError, ForbiddenError
from app.core.logging import get_logger
from app.modules.billing.application.support import expire_stale, order_not_found, sandbox
from app.modules.billing.domain.entities import Order
from app.modules.billing.domain.repositories import OrderRepository

log = get_logger(__name__)


class GetOrder:
    """Một đơn của xưởng — trang thanh toán hỏi lại vài giây một lần."""

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, actor: ActorContext, order_id: UUID) -> Order:
        await expire_stale(self._orders, actor.tenant_id)
        order = await self._orders.get(actor.tenant_id, order_id)
        if order is None:
            raise order_not_found()
        return order


class CancelOrder:
    """Huỷ đơn đang chờ trả (khách đổi ý hoặc muốn đổi cách trả)."""

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, actor: ActorContext, order_id: UUID) -> Order:
        """Raises: NotFoundError, ConflictError (đơn không còn chờ trả)."""
        if await self._orders.get(actor.tenant_id, order_id) is None:
            raise order_not_found()
        cancelled = await self._orders.cancel(actor.tenant_id, order_id)
        if cancelled is None:
            raise ConflictError("Đơn này không còn chờ thanh toán.", code="order_not_pending")
        return cancelled


class SimulatePayment:
    """Giả lập "đã chuyển khoản" để thử trọn luồng mua gói.

    CHỈ ở chế độ giả lập: Settings từ chối bật `PAYMENT_SANDBOX` ở
    staging/production, và use case kiểm lại lần nữa.
    """

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, actor: ActorContext, order_id: UUID) -> Order:
        if not sandbox():
            raise ForbiddenError("Chỉ dùng được ở chế độ giả lập thanh toán.", code="not_sandbox")
        order = await self._orders.get(actor.tenant_id, order_id)
        if order is None:
            raise order_not_found()
        paid = await self._orders.mark_paid(order_id, reference="SANDBOX", note="Giả lập")
        if paid is None:
            raise ConflictError("Đơn này không còn chờ thanh toán.", code="order_not_pending")
        log.info("order_paid_sandbox", code=order.code)
        return paid


__all__ = ["CancelOrder", "GetOrder", "SimulatePayment"]
