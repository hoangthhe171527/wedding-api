"""Use case: "Làm bìa" — đưa một ảnh lên đầu album (cùng cách thiết kế: order = min - 1)."""

from __future__ import annotations

from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import NotFoundError
from app.modules.media.domain.repositories import PhotoRepository


class MakeCover:
    """Đặt ảnh làm ảnh bìa."""

    def __init__(self, photos: PhotoRepository) -> None:
        self._photos = photos

    async def execute(self, actor: ActorContext, photo_id: UUID) -> None:
        photos = await self._photos.list(actor.tenant_id)
        if not any(item.id == photo_id for item in photos):
            raise NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")
        lowest = min(item.order for item in photos)
        await self._photos.set_order(actor.tenant_id, photo_id, lowest - 1)


__all__ = ["MakeCover"]
