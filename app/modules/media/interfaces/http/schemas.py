"""Schema HTTP của `media`."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.media.application.use_cases import PhotoView


class PhotoOut(BaseModel):
    """Một ảnh cưới. `url` đã ký, tự hết hạn — dùng thẳng trong `<img src>`."""

    id: UUID
    url: str
    order: int
    is_cover: bool
    width: int
    height: int
    focus_x: float
    focus_y: float
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
            focus_x=photo.focus_x,
            focus_y=photo.focus_y,
            size=photo.size,
            created_at=photo.created_at,
        )


def photos_out(views: list[PhotoView]) -> list[PhotoOut]:
    return [PhotoOut.of(view, is_cover=index == 0) for index, view in enumerate(views)]


class PhotoOrderIn(BaseModel):
    ids: list[UUID]


class PhotoFocusIn(BaseModel):
    focus_x: Annotated[float, Field(ge=0, le=100)]
    focus_y: Annotated[float, Field(ge=0, le=100)]


__all__ = ["PhotoFocusIn", "PhotoOrderIn", "PhotoOut", "photos_out"]
