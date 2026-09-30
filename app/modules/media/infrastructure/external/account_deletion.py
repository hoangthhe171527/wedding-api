"""Xoá metadata và object ảnh của một xưởng."""

from __future__ import annotations

from uuid import UUID

from app.core.storage import ObjectStore, get_object_store
from app.modules.media.infrastructure.persistence.models import PhotoBlobDocument, PhotoDocument


class AccountDataDeleter:
    def __init__(self, store: ObjectStore | None = None) -> None:
        self._store = store or get_object_store()

    async def execute(self, tenant_id: UUID) -> None:
        photos = await PhotoDocument.find({"tenant_id": tenant_id}).to_list()
        for photo in photos:
            if photo.small_key:
                await self._store.delete(photo.small_key)
            if photo.storage_key:
                await self._store.delete(photo.storage_key)
        await PhotoDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})
        await PhotoBlobDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})


def build_account_data_deleter() -> AccountDataDeleter:
    return AccountDataDeleter()


__all__ = ["AccountDataDeleter", "build_account_data_deleter"]
