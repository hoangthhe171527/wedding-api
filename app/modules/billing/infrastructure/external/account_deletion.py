"""Xử lý dữ liệu gói và thanh toán khi người dùng tự xoá tài khoản.

Sổ kế toán (`orders`, `payment_events`) và mã giao dịch Apple (`apple_purchases`)
phải giữ bất biến để đối soát tài chính và chống phát lại cùng `transaction_id` sang
tài khoản khác; chỉ ẩn danh ghi chú tự do trên đơn hàng.
"""

from __future__ import annotations

from uuid import UUID

from app.core import cache
from app.modules.billing.infrastructure.persistence.models import OrderDocument
from app.modules.billing.infrastructure.persistence.repositories import ENTITLEMENT_CACHE


class AccountDataDeleter:
    async def execute(self, tenant_id: UUID) -> None:
        await OrderDocument.get_motor_collection().update_many(
            {"tenant_id": tenant_id, "note": {"$ne": ""}},
            {"$set": {"note": "[account_deleted]"}},
        )
        await cache.delete(ENTITLEMENT_CACHE, str(tenant_id))


def build_account_data_deleter() -> AccountDataDeleter:
    return AccountDataDeleter()


__all__ = ["AccountDataDeleter", "build_account_data_deleter"]
