"""Xoá yêu cầu in thiệp giấy của một xưởng."""

from __future__ import annotations

from uuid import UUID

from app.modules.printing.infrastructure.persistence.models import PrintRequestDocument


class AccountDataDeleter:
    async def execute(self, tenant_id: UUID) -> None:
        await PrintRequestDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})


def build_account_data_deleter() -> AccountDataDeleter:
    return AccountDataDeleter()


__all__ = ["AccountDataDeleter", "build_account_data_deleter"]
