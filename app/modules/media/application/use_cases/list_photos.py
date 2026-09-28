"""Use case: album ảnh của xưởng, kèm URL đã ký."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.context import ActorContext
from app.modules.media.application.support import photo_url
from app.modules.media.domain.entities import Photo
from app.modules.media.domain.repositories import PhotoRepository


@dataclass(frozen=True, slots=True)
class PhotoView:
    photo: Photo
    url: str


class ListPhotos:
    """Ảnh theo thứ tự album; phần tử đầu là ảnh bìa."""

    def __init__(self, photos: PhotoRepository) -> None:
        self._photos = photos

    async def execute(self, actor: ActorContext) -> list[PhotoView]:
        return [
            PhotoView(photo=item, url=photo_url(item.id))
            for item in await self._photos.list(actor.tenant_id)
        ]


__all__ = ["ListPhotos", "PhotoView"]
