"""Xoá dữ liệu gói và thanh toán gắn với xưởng."""

from __future__ import annotations

from uuid import UUID

from app.modules.billing.infrastructure.persistence.models import (
    ApplePurchaseDocument,
    OrderDocument,
    PaymentEventDocument,
)


class AccountDataDeleter:
    async def execute(self, tenant_id: UUID) -> None:
        await OrderDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})
        await PaymentEventDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})
        await ApplePurchaseDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})


def build_account_data_deleter() -> AccountDataDeleter:
    return AccountDataDeleter()


__all__ = ["AccountDataDeleter", "build_account_data_deleter"]
