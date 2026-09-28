"""Use case: xoá một ảnh khỏi album (xoá cứng cả byte ảnh)."""

from __future__ import annotations

from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import NotFoundError
from app.modules.media.domain.repositories import PhotoRepository


class DeletePhoto:
    """Xoá ảnh trong phạm vi xưởng của actor; ngoài phạm vi -> 404."""

    def __init__(self, photos: PhotoRepository) -> None:
        self._photos = photos

    async def execute(self, actor: ActorContext, photo_id: UUID) -> None:
        if not await self._photos.delete(actor.tenant_id, photo_id):
            raise NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")


__all__ = ["DeletePhoto"]
