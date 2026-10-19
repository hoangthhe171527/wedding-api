"""Thực thể thuần của `media`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final
from uuid import UUID

#: Định dạng lưu sau khi chuẩn hoá — trình duyệt nào cũng hiển thị được.
STORED_TYPES: Final[frozenset[str]] = frozenset({"image/jpeg", "image/png"})

#: Bộ lọc màu của trình chỉnh ảnh — khoá trùng `PHOTO_FILTERS` phía web (`contracts/enums.json`).
PHOTO_FILTERS: Final[tuple[str, ...]] = ("goc", "nga", "phim", "trong", "hoang", "den")
#: Xoay theo bước vuông góc: ảnh luôn phủ kín khung, không lộ góc trống.
PHOTO_ROTATIONS: Final[tuple[int, ...]] = (0, 90, 180, 270)
ZOOM_RANGE: Final[tuple[float, float]] = (1.0, 3.0)
#: Độ sáng / tương phản / bão hoà / độ ấm: 0 = giữ nguyên ảnh.
TONE_RANGE: Final[tuple[int, int]] = (-50, 50)
MAX_CAPTION: Final[int] = 80


@dataclass(frozen=True, slots=True)
class PhotoAdjust:
    """Chỉnh ảnh không phá huỷ: byte ảnh giữ nguyên, web thiệp áp lúc hiển thị.

    Attributes:
        zoom: Phóng to quanh điểm trọng tâm (1 = vừa khung).
        filter_strength: Cường độ bộ lọc, phần trăm.
        caption: Chú thích; hiện dưới ảnh ở khung Polaroid và làm chữ thay thế.
    """

    zoom: float = 1.0
    rotate: int = 0
    flip: bool = False
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    warmth: int = 0
    filter: str = "goc"
    filter_strength: int = 100
    caption: str = ""


#: Tên trường chỉnh ảnh — đúng tên cột trong `photos` và tên trường của API.
ADJUST_FIELDS: Final[tuple[str, ...]] = tuple(PhotoAdjust.__dataclass_fields__)


def clean_caption(caption: str) -> str:
    """Một dòng, không khoảng trắng thừa — chú thích nằm gọn dưới ảnh."""
    return " ".join(caption.split())


def adjust_problem(adjust: PhotoAdjust) -> str | None:
    """Câu báo lỗi đầu tiên của bộ chỉnh ảnh; None là hợp lệ."""
    low, high = ZOOM_RANGE
    if not low <= adjust.zoom <= high:
        return f"Độ phóng to từ {low:g} đến {high:g} lần."
    if adjust.rotate not in PHOTO_ROTATIONS:
        return "Chỉ xoay ảnh theo bước 90 độ."
    tone_low, tone_high = TONE_RANGE
    for value in (adjust.brightness, adjust.contrast, adjust.saturation, adjust.warmth):
        if not tone_low <= value <= tone_high:
            return f"Độ sáng, tương phản, bão hoà và độ ấm từ {tone_low} đến {tone_high}."
    if adjust.filter not in PHOTO_FILTERS:
        return "Bộ lọc không có trong danh sách."
    if not 0 <= adjust.filter_strength <= 100:
        return "Cường độ bộ lọc từ 0 đến 100%."
    if len(adjust.caption) > MAX_CAPTION:
        return f"Chú thích tối đa {MAX_CAPTION} ký tự."
    return None


@dataclass(frozen=True, slots=True)
class Photo:
    """Siêu dữ liệu một ảnh cưới (byte ảnh nằm riêng, không tải kèm danh sách).

    Attributes:
        order: Thứ tự trong album; ảnh có `order` nhỏ nhất là ẢNH BÌA.
    """

    id: UUID
    tenant_id: UUID
    order: int
    content_type: str
    size: int
    width: int
    height: int
    content_hash: str = ""
    focus_x: float = 50.0
    focus_y: float = 50.0
    adjust: PhotoAdjust = field(default_factory=PhotoAdjust)
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    """Ảnh đã chuẩn hoá: xoay đúng chiều, thu nhỏ, bỏ EXIF."""

    data: bytes
    content_type: str
    width: int
    height: int
    #: Bản nhỏ (ngang `SMALL_WIDTH`) cho điện thoại; None khi ảnh gốc đã đủ nhỏ.
    small: bytes | None = None


__all__ = [
    "ADJUST_FIELDS",
    "MAX_CAPTION",
    "PHOTO_FILTERS",
    "PHOTO_ROTATIONS",
    "STORED_TYPES",
    "TONE_RANGE",
    "ZOOM_RANGE",
    "Photo",
    "PhotoAdjust",
    "ProcessedImage",
    "adjust_problem",
    "clean_caption",
]
