"""Use case: ghi nhận tiền về từ ngân hàng (webhook chuyển khoản) và từ MoMo (IPN).

Luật chung cho cả hai nguồn:

* Mỗi giao dịch ghi một dòng vào `payment_events` với khoá `(nguồn, mã giao
  dịch)` duy nhất — nguồn gửi lại cùng giao dịch (khi chưa nhận 200) thì lần
  sau chỉ gặp lỗi trùng và dừng, không bao giờ kích hoạt gói hai lần.
* Chỉ kích hoạt khi số tiền về ĐỦ số tiền của đơn. Thiếu thì ghi "trả thiếu"
  để đội vận hành xử lý tay, không tự kích hoạt.
* Tiền về không khớp đơn nào vẫn được ghi ("không khớp") để đối soát.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.errors import NotFoundError, UnauthorizedError
from app.core.logging import get_logger
from app.modules.billing.domain.entities import Order
from app.modules.billing.domain.enums import OrderStatus, PaymentEventStatus, PaymentMethod
from app.modules.billing.domain.repositories import (
    DuplicatePaymentEventError,
    OrderRepository,
    PaymentEventRepository,
)
from app.modules.billing.domain.services import find_order_code, momo_signature_valid

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class BankTransfer:
    """Một giao dịch tiền VÀO tài khoản, theo định dạng webhook của dịch vụ đọc sao kê."""

    external_id: str
    amount: int
    content: str
    direction: str
    raw: dict[str, Any]


def _classify(order: Order | None, amount: int) -> PaymentEventStatus:
    if order is None:
        return PaymentEventStatus.UNMATCHED
    if order.status is OrderStatus.PAID:
        return PaymentEventStatus.DUPLICATE
    if order.status is OrderStatus.CANCELLED:
        return PaymentEventStatus.UNMATCHED
    if amount < order.amount:
        return PaymentEventStatus.UNDERPAID
    return PaymentEventStatus.MATCHED


def _ensure_online_payment() -> None:
    """Luồng nâng gói qua Zalo (mặc định): webhook thanh toán coi như không tồn tại.

    Để webhook mở khi không dùng là để thêm một cửa ai cũng thử gõ được.
    """
    if not get_settings().ONLINE_PAYMENT_ENABLED:
        raise NotFoundError("Không tìm thấy dữ liệu.")


async def _settle(
    orders: OrderRepository,
    events: PaymentEventRepository,
    *,
    source: str,
    external_id: str,
    amount: int,
    content: str,
    order: Order | None,
    raw: dict[str, Any],
) -> PaymentEventStatus:
    status = _classify(order, amount)
    # Kích hoạt đơn TRƯỚC, ghi sổ SAU. \`mark_paid\` chỉ đổi đơn còn chờ / hết hạn nên
    # gọi lại bao nhiêu lần cũng được. Ngược thứ tự (như trước) thì tiến trình chết
    # giữa hai bước để lại sổ "đã khớp" + đơn vẫn chờ, và ngân hàng gửi lại chỉ nhận
    # "trùng" — khách đã trả tiền mà không bao giờ có gói.
    if status is PaymentEventStatus.MATCHED and order is not None:
        paid = await orders.mark_paid(order.id, reference=f"{source}:{external_id}")
        if paid is None:
            # Một báo có khác đã kích hoạt đơn này trước (hoặc lần gửi trước đã kịp).
            status = PaymentEventStatus.DUPLICATE
        else:
            log.info("order_paid", code=order.code, source=source, amount=amount)
    try:
        await events.record(
            source=source,
            external_id=external_id,
            amount=amount,
            content=content,
            status=status,
            order_code=order.code if order else "",
            tenant_id=order.tenant_id if order else None,
            raw=raw,
        )
    except DuplicatePaymentEventError:
        log.info("payment_event_duplicate", source=source, external_id=external_id)
        return PaymentEventStatus.DUPLICATE
    if status is not PaymentEventStatus.MATCHED:
        log.warning("payment_needs_review", source=source, status=status.value, amount=amount)
    return status


class RecordBankTransfer:
    """Webhook báo có của tài khoản nhận tiền."""

    def __init__(self, orders: OrderRepository, events: PaymentEventRepository) -> None:
        self._orders = orders
        self._events = events

    async def execute(self, api_key: str, transfer: BankTransfer) -> PaymentEventStatus:
        """Raises: NotFoundError (thanh toán online tắt), UnauthorizedError (khoá sai)."""
        _ensure_online_payment()
        expected = get_settings().BANK_WEBHOOK_KEY
        if not expected or not _same(api_key, expected):
            raise UnauthorizedError("Khoá webhook không hợp lệ.", code="webhook_unauthorized")
        if transfer.direction != "in" or transfer.amount <= 0:
            return PaymentEventStatus.IGNORED
        code = find_order_code(transfer.content)
        order = await self._orders.find_by_code(code) if code else None
        if order is not None and order.method is not PaymentMethod.BANK_TRANSFER:
            # Khách tạo đơn MoMo rồi lại chuyển khoản theo mã đó: vẫn là tiền của đơn.
            log.info("bank_transfer_for_momo_order", code=order.code)
        return await _settle(
            self._orders,
            self._events,
            source="bank",
            external_id=transfer.external_id,
            amount=transfer.amount,
            content=transfer.content,
            order=order,
            raw=transfer.raw,
        )


class RecordMomoIpn:
    """IPN của MoMo — chữ ký HMAC bắt buộc đúng."""

    def __init__(self, orders: OrderRepository, events: PaymentEventRepository) -> None:
        self._orders = orders
        self._events = events

    async def execute(self, payload: dict[str, Any]) -> PaymentEventStatus:
        """Raises: NotFoundError (thanh toán online tắt), UnauthorizedError (chữ ký sai)."""
        _ensure_online_payment()
        cfg = get_settings()
        signature = str(payload.get("signature", ""))
        if not (
            cfg.MOMO_SECRET_KEY
            and momo_signature_valid(cfg.MOMO_SECRET_KEY, cfg.MOMO_ACCESS_KEY, payload, signature)
        ):
            raise UnauthorizedError("Chữ ký MoMo không hợp lệ.", code="momo_signature")
        if str(payload.get("resultCode")) != "0":
            return PaymentEventStatus.IGNORED
        order = await self._orders.find_by_code(str(payload.get("orderId", "")))
        try:
            amount = int(str(payload.get("amount", "0")))
        except ValueError:
            amount = 0
        return await _settle(
            self._orders,
            self._events,
            source="momo",
            external_id=str(payload.get("transId", "")),
            amount=amount,
            content=str(payload.get("orderInfo", "")),
            order=order,
            raw=payload,
        )


def _same(given: str, expected: str) -> bool:
    return hmac.compare_digest(given.encode(), expected.encode())


__all__ = ["BankTransfer", "RecordBankTransfer", "RecordMomoIpn"]
