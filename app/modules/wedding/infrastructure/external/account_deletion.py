"""Xoá đám cưới và cache link công khai khi tài khoản bị xoá."""

from __future__ import annotations

from uuid import UUID

from app.core import cache
from app.modules.wedding.infrastructure.persistence.models import WeddingDocument
from app.modules.wedding.infrastructure.persistence.repositories import PUBLISHED_CACHE


class AccountDataDeleter:
    async def execute(self, tenant_id: UUID) -> None:
        weddings = await WeddingDocument.find({"tenant_id": tenant_id}).to_list()
        await WeddingDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})
        for wedding in weddings:
            await cache.delete(PUBLISHED_CACHE, wedding.slug)


def build_account_data_deleter() -> AccountDataDeleter:
    return AccountDataDeleter()


__all__ = ["AccountDataDeleter", "build_account_data_deleter"]
