"""Quy tắc thuần của thư viện video mở thiệp: nhận dạng định dạng, đặt tên."""

from __future__ import annotations

from pathlib import PurePath
from typing import Final

#: Tên video tối đa (hiện ở bộ chọn của cặp đôi và màn quản trị).
INTRO_NAME_MAX: Final[int] = 80
#: Tên khi tệp tải lên không có tên dùng được.
INTRO_FALLBACK_NAME: Final[str] = "Video mở thiệp"

MP4: Final[str] = "video/mp4"
WEBM: Final[str] = "video/webm"
#: Định dạng `<video>` của mọi trình duyệt phát được (WebM: trừ Safari cũ).
INTRO_TYPES: Final[frozenset[str]] = frozenset({MP4, WEBM})
EXTENSIONS: Final[dict[str, str]] = {MP4: "mp4", WEBM: "webm"}

#: Chữ ký EBML ở đầu mọi tệp WebM/Matroska.
_EBML_MAGIC: Final[bytes] = b"\x1a\x45\xdf\xa3"


def sniff_video(data: bytes) -> str | None:
    """Content type theo BYTE ĐẦU tệp, không tin tên tệp hay header client gửi.

    MP4 (ISO BMFF): hộp đầu tiên là `ftyp` — byte 4..8. WebM: bắt đầu bằng EBML.
    Không nhận ra thì trả None.
    """
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return MP4
    if data.startswith(_EBML_MAGIC):
        return WEBM
    return None


def intro_name(name: str | None, filename: str | None) -> str:
    """Tên gửi kèm; trống thì lấy tên tệp bỏ đuôi — luôn cắt còn `INTRO_NAME_MAX` ký tự."""
    chosen = (name or "").strip() or PurePath(filename or "").stem.strip()
    return (chosen or INTRO_FALLBACK_NAME)[:INTRO_NAME_MAX].strip()


__all__ = [
    "EXTENSIONS",
    "INTRO_FALLBACK_NAME",
    "INTRO_NAME_MAX",
    "INTRO_TYPES",
    "MP4",
    "WEBM",
    "intro_name",
    "sniff_video",
]
