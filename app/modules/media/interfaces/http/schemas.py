"""Schema HTTP của `media`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.media.application.use_cases import PhotoView


class PhotoOut(BaseModel):
    """Một ảnh cưới. `url` đã ký, tự hết hạn — dùng thẳng trong `<img src>`."""

    id: UUID
    url: str
    order: int
    is_cover: bool
    width: int
    height: int
    size: int
    created_at: datetime | None = None

    @classmethod
    def of(cls, view: PhotoView, *, is_cover: bool) -> PhotoOut:
        photo = view.photo
        return cls(
            id=photo.id,
            url=view.url,
            order=photo.order,
            is_cover=is_cover,
            width=photo.width,
            height=photo.height,
            size=photo.size,
            created_at=photo.created_at,
        )


def photos_out(views: list[PhotoView]) -> list[PhotoOut]:
    return [PhotoOut.of(view, is_cover=index == 0) for index, view in enumerate(views)]


__all__ = ["PhotoOut", "photos_out"]
