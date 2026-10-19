"""Schema HTTP của `media`."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.media.application.use_cases import PhotoView
from app.modules.media.domain.entities import MAX_CAPTION, TONE_RANGE, ZOOM_RANGE


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
    zoom: float
    rotate: int
    flip: bool
    brightness: int
    contrast: int
    saturation: int
    warmth: int
    filter: str
    filter_strength: int
    caption: str
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
            **asdict(photo.adjust),
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


Tone = Annotated[int, Field(ge=TONE_RANGE[0], le=TONE_RANGE[1])]


class PhotoAdjustIn(BaseModel):
    """Chỉnh ảnh — gửi trường nào ghi trường đó. Miền giá trị: `media/domain/entities.py`."""

    focus_x: Annotated[float, Field(ge=0, le=100)] | None = None
    focus_y: Annotated[float, Field(ge=0, le=100)] | None = None
    zoom: Annotated[float, Field(ge=ZOOM_RANGE[0], le=ZOOM_RANGE[1])] | None = None
    rotate: Literal[0, 90, 180, 270] | None = None
    flip: bool | None = None
    brightness: Tone | None = None
    contrast: Tone | None = None
    saturation: Tone | None = None
    warmth: Tone | None = None
    filter: Literal["goc", "nga", "phim", "trong", "hoang", "den"] | None = None
    filter_strength: Annotated[int, Field(ge=0, le=100)] | None = None
    caption: Annotated[str, Field(max_length=MAX_CAPTION * 2)] | None = None


__all__ = ["PhotoAdjustIn", "PhotoFocusIn", "PhotoOrderIn", "PhotoOut", "photos_out"]
