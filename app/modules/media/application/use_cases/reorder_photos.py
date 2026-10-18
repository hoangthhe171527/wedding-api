"""Use case: đổi thứ tự album ảnh cưới."""

from __future__ import annotations

from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import ValidationError
from app.modules.media.domain.repositories import PhotoRepository


class ReorderPhotos:
    def __init__(self, photos: PhotoRepository) -> None:
        self._photos = photos

    async def execute(self, actor: ActorContext, ordered_ids: list[UUID]) -> None:
        current = await self._photos.list(actor.tenant_id)
        current_ids = [item.id for item in current]
        if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != set(current_ids):
            raise ValidationError(
                "Danh sách sắp xếp không khớp album hiện tại. Hãy tải lại trang rồi thử lại.",
                code="photo_order_invalid",
            )
        for order, photo_id in enumerate(ordered_ids):
            await self._photos.set_order(actor.tenant_id, photo_id, order)


__all__ = ["ReorderPhotos"]
