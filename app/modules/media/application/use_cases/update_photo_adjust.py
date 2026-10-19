"""Use case: chỉnh ảnh (căn, phóng to, xoay, lật, màu, bộ lọc, chú thích)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any
from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import NotFoundError, ValidationError
from app.modules.media.domain.entities import (
    ADJUST_FIELDS,
    adjust_problem,
    clean_caption,
)
from app.modules.media.domain.repositories import PhotoRepository

_FOCUS_FIELDS = ("focus_x", "focus_y")


class UpdatePhotoAdjust:
    """Ghi ĐÚNG những trường được gửi: kéo thanh màu và chọn bộ lọc liền nhau không đè nhau."""

    def __init__(self, photos: PhotoRepository) -> None:
        self._photos = photos

    async def execute(
        self, actor: ActorContext, photo_id: UUID, changes: Mapping[str, Any]
    ) -> None:
        unknown = set(changes) - {*ADJUST_FIELDS, *_FOCUS_FIELDS}
        if unknown:
            raise ValidationError("Trường chỉnh ảnh không hợp lệ.", code="photo_adjust_invalid")
        photo = await self._photos.get(actor.tenant_id, photo_id)
        if photo is None:
            raise NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")

        fields = dict(changes)
        if "caption" in fields:
            fields["caption"] = clean_caption(str(fields["caption"]))
        if any(not 0 <= fields.get(name, 50) <= 100 for name in _FOCUS_FIELDS):
            raise ValidationError("Điểm căn ảnh phải nằm trong khung.", code="photo_focus_invalid")
        adjust = replace(
            photo.adjust, **{key: value for key, value in fields.items() if key in ADJUST_FIELDS}
        )
        problem = adjust_problem(adjust)
        if problem:
            raise ValidationError(problem, code="photo_adjust_invalid")
        if fields and not await self._photos.set_adjust(actor.tenant_id, photo_id, fields):
            raise NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")


__all__ = ["UpdatePhotoAdjust"]
