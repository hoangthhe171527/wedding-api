"""Use case: đặt điểm trọng tâm để căn ảnh trong mọi khung cover."""

from __future__ import annotations

from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import NotFoundError, ValidationError
from app.modules.media.domain.repositories import PhotoRepository


class UpdatePhotoFocus:
    def __init__(self, photos: PhotoRepository) -> None:
        self._photos = photos

    async def execute(
        self, actor: ActorContext, photo_id: UUID, *, focus_x: float, focus_y: float
    ) -> None:
        if not 0 <= focus_x <= 100 or not 0 <= focus_y <= 100:
            raise ValidationError("Điểm căn ảnh phải nằm trong khung.", code="photo_focus_invalid")
        if not await self._photos.set_focus(
            actor.tenant_id, photo_id, focus_x=focus_x, focus_y=focus_y
        ):
            raise NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")


__all__ = ["UpdatePhotoFocus"]
