"""Bộ điều hợp `ImageProcessor` bằng Pillow."""

from __future__ import annotations

import io
import warnings
from typing import Final

from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.media.application.ports import UnreadableImageError
from app.modules.media.domain.entities import ProcessedImage

#: Cạnh dài tối đa sau khi thu nhỏ — đủ nét trên màn hình điện thoại 3x.
MAX_EDGE: Final[int] = 1600
#: Bề ngang bản nhỏ: đủ nét cho khung ảnh trên điện thoại (360-430px x DPR 2),
#: nặng chừng 1/4 bản đầy đủ. Web thiệp chọn qua `srcset`.
SMALL_WIDTH: Final[int] = 800
#: Trần điểm ảnh khi GIẢI NÉN: chặn "bom giải nén" (ảnh vài KB nở ra hàng GB RAM).
MAX_PIXELS: Final[int] = 40_000_000
JPEG_QUALITY: Final[int] = 85
ACCEPTED_FORMATS: Final[frozenset[str]] = frozenset({"JPEG", "PNG", "WEBP", "MPO"})


class PillowImageProcessor:
    """Xoay theo EXIF, thu nhỏ, mã hoá lại — không mang theo siêu dữ liệu nào."""

    def process(self, data: bytes) -> ProcessedImage:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                with Image.open(io.BytesIO(data)) as probe:
                    fmt = probe.format or ""
                    if fmt not in ACCEPTED_FORMATS:
                        raise UnreadableImageError(fmt)
                    if probe.width * probe.height > MAX_PIXELS:
                        raise UnreadableImageError("too_many_pixels")
                    probe.verify()
                # `verify()` làm ảnh không dùng được nữa — mở lại để đọc điểm ảnh.
                with Image.open(io.BytesIO(data)) as source:
                    # JPEG: giải mã thẳng ở độ phân giải gần cỡ đích (1/2, 1/4, 1/8) thay
                    # vì bung cả ảnh gốc ra RAM rồi mới thu nhỏ. Không ảnh hưởng EXIF.
                    source.draft("RGB", (MAX_EDGE, MAX_EDGE))
                    image = ImageOps.exif_transpose(source)
                    image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
                    data, content_type = _encode(image)
                    return ProcessedImage(
                        data=data,
                        content_type=content_type,
                        width=image.width,
                        height=image.height,
                        small=_small(image),
                    )
            except (
                UnidentifiedImageError,
                OSError,
                SyntaxError,
                Image.DecompressionBombWarning,
            ) as exc:
                raise UnreadableImageError(str(exc)) from exc

    def small_variant(self, data: bytes) -> bytes | None:
        """Bản nhỏ từ ảnh ĐÃ chuẩn hoá (đã bỏ EXIF) — cho ảnh tải lên trước khi có bản nhỏ."""
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            return _small(source)


def _encode(image: Image.Image) -> tuple[bytes, str]:
    out = io.BytesIO()
    has_alpha = image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)
    if has_alpha:
        image.convert("RGBA").save(out, format="PNG", optimize=True)
        return out.getvalue(), "image/png"
    image.convert("RGB").save(
        out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True
    )
    return out.getvalue(), "image/jpeg"


def _small(image: Image.Image) -> bytes | None:
    """Cùng định dạng với bản đầy đủ (URL hai bản dùng chung content type)."""
    if image.width <= SMALL_WIDTH:
        return None
    height = max(1, round(image.height * SMALL_WIDTH / image.width))
    return _encode(image.resize((SMALL_WIDTH, height), Image.Resampling.LANCZOS))[0]


__all__ = ["SMALL_WIDTH", "PillowImageProcessor"]
