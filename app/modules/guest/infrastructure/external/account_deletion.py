"""Xoá khách mời và lời chúc khi tài khoản bị xoá."""

from __future__ import annotations

from uuid import UUID

from app.modules.guest.infrastructure.persistence.models import GuestDocument, WishDocument


class AccountDataDeleter:
    async def execute(self, tenant_id: UUID) -> None:
        await GuestDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})
        await WishDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})


def build_account_data_deleter() -> AccountDataDeleter:
    return AccountDataDeleter()


__all__ = ["AccountDataDeleter", "build_account_data_deleter"]
