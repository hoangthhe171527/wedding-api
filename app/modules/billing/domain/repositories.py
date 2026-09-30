"""Hợp đồng lưu trữ của `billing`."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.core.pages import Page, PageParams
from app.modules.billing.domain.entities import ApplePurchase, Order, PaymentEvent
from app.modules.billing.domain.enums import (
    OrderStatus,
    PaymentEventStatus,
    PaymentMethod,
    Plan,
)


class OrderCodeTakenError(Exception):
    """Mã đơn đã có (index duy nhất từ chối) — sinh mã khác rồi thử lại."""


class DuplicatePaymentEventError(Exception):
    """Báo có này đã được ghi — ngân hàng / cổng gửi lại cùng một giao dịch."""


class OrderRepository(Protocol):
    """Truy cập collection `orders`."""

    async def create(
        self,
        *,
        tenant_id: UUID,
        code: str,
        plan: Plan,
        amount: int,
        method: PaymentMethod,
        expires_at: datetime,
        actor_id: UUID,
    ) -> Order:
        """Raises: OrderCodeTakenError."""
        ...

    async def get(self, tenant_id: UUID, order_id: UUID) -> Order | None: ...

    async def get_any(self, order_id: UUID) -> Order | None:
        """Theo id, không lọc xưởng — chỉ cho đội vận hành (quyền kiểm ở router)."""
        ...

    async def find_by_code(self, code: str) -> Order | None:
        """Theo mã đơn, toàn hệ thống — webhook ngân hàng chưa biết xưởng (§0.4)."""
        ...

    async def list_for_tenant(self, tenant_id: UUID) -> list[Order]:
        """Đơn của một xưởng, mới nhất trước."""
        ...

    async def list_page(self, params: PageParams, status: OrderStatus | None) -> Page[Order]:
        """Mọi đơn (màn đối soát của đội vận hành), mới nhất trước."""
        ...

    async def paid_plans(self, tenant_id: UUID) -> list[Plan]: ...

    async def open_order(self, tenant_id: UUID, plan: Plan, method: PaymentMethod) -> Order | None:
        """Đơn đang chờ trả, còn hạn, cùng gói và cách trả — dùng lại thay vì tạo mới."""
        ...

    async def set_pay_url(self, order_id: UUID, pay_url: str) -> None: ...

    async def mark_paid(self, order_id: UUID, *, reference: str, note: str = "") -> Order | None:
        """Chờ trả -> đã trả, NGUYÊN TỬ. Trả None nếu đơn không còn ở trạng thái chờ."""
        ...

    async def cancel(self, tenant_id: UUID, order_id: UUID) -> Order | None:
        """Huỷ đơn đang chờ trả của xưởng."""
        ...

    async def paid_plans_many(self, tenant_ids: list[UUID]) -> dict[UUID, list[Plan]]:
        """Gói đã trả của nhiều xưởng trong MỘT lượt truy vấn (màn quản trị)."""
        ...

    async def expire_due(self, now: datetime, tenant_id: UUID | None = None) -> int:
        """Đơn chờ quá hạn -> hết hạn; `tenant_id` = chỉ của một xưởng."""
        ...


class PaymentEventRepository(Protocol):
    """Truy cập collection `payment_events` — sổ báo có để đối soát."""

    async def record(
        self,
        *,
        source: str,
        external_id: str,
        amount: int,
        content: str,
        status: PaymentEventStatus,
        order_code: str,
        tenant_id: UUID | None,
        raw: dict[str, object],
    ) -> PaymentEvent:
        """Raises: DuplicatePaymentEventError (cùng `source` + `external_id`)."""
        ...

    async def list_recent(self, limit: int) -> list[PaymentEvent]: ...


class ApplePurchaseRepository(Protocol):
    """Sổ giao dịch Apple đã xác thực, dùng để chống cấp quyền lặp / chuyển tài khoản."""

    async def get_by_transaction_id(self, transaction_id: str) -> ApplePurchase | None: ...

    async def create(
        self,
        *,
        transaction_id: str,
        original_transaction_id: str,
        product_id: str,
        plan: Plan,
        environment: str,
        tenant_id: UUID,
        purchase_date: datetime,
    ) -> ApplePurchase: ...


__all__ = [
    "ApplePurchaseRepository",
    "DuplicatePaymentEventError",
    "OrderCodeTakenError",
    "OrderRepository",
    "PaymentEventRepository",
]
