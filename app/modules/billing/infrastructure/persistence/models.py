"""Beanie Document của `billing` — collection `orders` và `payment_events`."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from pydantic import Field

from app.core.base_model import (
    ASCENDING,
    DESCENDING,
    BaseDocument,
    Document,
    IndexModel,
    TenantScopedDocument,
)


class OrderDocument(TenantScopedDocument):
    """Một đơn mua gói của một xưởng."""

    code: str
    plan: str
    amount: int
    method: str
    status: str = "pending"
    expires_at: datetime
    paid_at: datetime | None = None
    pay_url: str = ""
    reference: str = ""
    note: str = ""

    class Settings(TenantScopedDocument.Settings):
        name = "orders"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            # Ngoại lệ có chủ ý với §0.4: webhook ngân hàng chỉ mang nội dung
            # chuyển khoản — tra đơn theo mã khi CHƯA biết xưởng.
            IndexModel([("code", ASCENDING)], name="uq_orders_code", unique=True),
            IndexModel(
                [("tenant_id", ASCENDING), ("status", ASCENDING), ("plan", ASCENDING)],
                name="ix_orders_tenant_status",
            ),
            IndexModel(
                [("status", ASCENDING), ("created_at", DESCENDING)], name="ix_orders_status"
            ),
            # Quét đơn quá hạn (màn đối soát) và danh sách mọi đơn mới nhất trước.
            IndexModel([("status", ASCENDING), ("expires_at", ASCENDING)], name="ix_orders_expiry"),
            IndexModel(
                [("deleted_at", ASCENDING), ("created_at", DESCENDING)], name="ix_orders_recent"
            ),
        ]


class PaymentEventDocument(BaseDocument):
    """Một báo có tiền về, lưu nguyên văn để đối soát.

    Ngoại lệ có chủ ý với §0.4 (không bắt buộc `tenant_id`): tiền về mà không
    khớp đơn nào thì chưa biết của xưởng nào — đó chính là thứ cần đối soát tay.
    """

    source: str
    external_id: str
    amount: int
    content: str = ""
    status: str
    order_code: str = ""
    tenant_id: UUID | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    class Settings(BaseDocument.Settings):
        name = "payment_events"
        indexes: ClassVar[list[IndexModel]] = [
            # Ngân hàng / cổng gửi lại cùng giao dịch khi chưa nhận được 200.
            IndexModel(
                [("source", ASCENDING), ("external_id", ASCENDING)],
                name="uq_payment_events_source_id",
                unique=True,
            ),
            IndexModel([("created_at", DESCENDING)], name="ix_payment_events_created"),
        ]


DOCUMENTS: list[type[Document]] = [OrderDocument, PaymentEventDocument]

__all__ = ["DOCUMENTS", "OrderDocument", "PaymentEventDocument"]
