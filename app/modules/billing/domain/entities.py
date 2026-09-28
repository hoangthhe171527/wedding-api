"""Thực thể thuần của `billing`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.billing.domain.enums import (
    OrderStatus,
    PaymentEventStatus,
    PaymentMethod,
    Plan,
)


@dataclass(frozen=True, slots=True)
class Order:
    """Một đơn mua gói cho một xưởng.

    Attributes:
        code: Mã đơn khách ghi vào nội dung chuyển khoản (vd `TH7KQ2M9XR4P`).
            Duy nhất toàn hệ thống: webhook ngân hàng chỉ mang nội dung chuyển
            khoản, chưa biết xưởng nào.
        amount: Số tiền phải trả — đã trừ giá gói đang có khi nâng cấp.
        pay_url: Link trang thanh toán của cổng (MoMo); rỗng với chuyển khoản.
        reference: Mã giao dịch phía ngân hàng / cổng khi đã trả.
    """

    id: UUID
    tenant_id: UUID
    code: str
    plan: Plan
    amount: int
    method: PaymentMethod
    status: OrderStatus
    expires_at: datetime
    created_at: datetime
    paid_at: datetime | None = None
    pay_url: str = ""
    reference: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    """Một báo có tiền về từ ngân hàng hoặc cổng thanh toán — lưu nguyên để đối soát."""

    id: UUID
    source: str
    external_id: str
    amount: int
    content: str
    status: PaymentEventStatus
    received_at: datetime
    order_code: str = ""
    tenant_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Usage:
    """Những gì một đám cưới đang dùng — dữ liệu thuần do `wedding` gom và gửi sang."""

    templates: frozenset[str]
    open_style: str
    guest_count: int
    music: bool
    gift: bool
    theme: bool
    design: bool = False


@dataclass(frozen=True, slots=True)
class Violation:
    """Một thứ đang dùng vượt quyền của gói hiện tại."""

    code: str
    message: str
    plan: Plan


__all__ = ["Order", "PaymentEvent", "Usage", "Violation"]
