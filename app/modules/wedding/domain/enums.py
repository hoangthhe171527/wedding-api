"""Enum và hằng của `wedding` — khớp nguyên văn thiết kế Xưởng Thiệp Hỷ."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class EventKind(StrEnum):
    """Loại sự kiện: lễ tại gia hay tiệc cưới.

    Thiệp in lấy sự kiện `tiec` đầu tiên khách được mời; web thiệp liệt kê đủ.
    """

    LE = "le"
    TIEC = "tiec"


class Side(StrEnum):
    """Sự kiện thuộc nhà nào."""

    TRAI = "trai"
    GAI = "gai"
    CHUNG = "chung"


class OpenStyle(StrEnum):
    """Màn mở thiệp — hiệu ứng khách thấy đầu tiên khi mở link."""

    BY_TEMPLATE = ""
    ANIMATION_3D = "3d"
    PARTICLES = "particles"
    ENVELOPE = "env"
    MIXED = "mix"
    FOLD = "fold"
    GATE = "gate"
    LOTUS = "lotus"
    SCROLL = "scroll"
    GIFT_BOX = "box"


class Tone(StrEnum):
    """Giọng văn — bản CHÉP của `template.domain.enums.Tone` (§1.2: không import chéo)."""

    FAMILY = "family"
    FORMAL = "formal"
    FRIENDS = "friends"


#: Nhóm khách — bản CHÉP của `guest.domain.enums.GUEST_GROUPS` (§1.2). Hai bản
#: phải trùng nhau; `tests/modules/test_parity.py` khoá điều đó.
GUEST_GROUPS: Final[tuple[str, ...]] = (
    "Họ hàng",
    "Bạn bố mẹ",
    "Hàng xóm",
    "Thầy cô",
    "Đồng nghiệp",
    "Đối tác",
    "Bạn bè",
)

#: Các ô câu chữ tuỳ chỉnh được theo giọng văn (`eyebrowG` chỉ có nghĩa với
#: giọng gia đình — tiêu đề riêng cho khách nhà gái, mặc định "Lễ Vu Quy").
WORDING_KEYS: Final[frozenset[str]] = frozenset(
    {"eyebrow", "eyebrowG", "invite", "announce", "attend", "closing", "thanks"}
)

#: Lộ trình chuẩn bị (tab Kế hoạch) — id cố định để tiến độ đánh dấu sống qua
#: các lần sửa câu chữ ở web.
CHECKLIST_IDS: Final[tuple[str, ...]] = tuple(f"c{index}" for index in range(1, 12))

MAX_EVENTS: Final[int] = 12
#: Ảnh QR mừng cưới lưu dạng data URL (PNG/JPEG/WebP đã thu nhỏ ở trình duyệt): ~150 KB.
MAX_QR_CHARS: Final[int] = 200_000

#: Font được chọn ở bộ chỉnh giao diện — đúng các font web thiệp đã nạp sẵn
#: (Google Fonts, có đủ dấu tiếng Việt). Font lạ sẽ rơi về font dự phòng.
THEME_FONTS: Final[frozenset[str]] = frozenset(
    {
        "Alex Brush",
        "Be Vietnam Pro",
        "Big Shoulders Display",
        "Birthstone",
        "Bonheur Royale",
        "Carattere",
        "Corinthia",
        "Cormorant Garamond",
        "Fraunces",
        "Great Vibes",
        "Imperial Script",
        "Lavishly Yours",
        "Lora",
        "Luxurious Script",
        "Manrope",
        "Newsreader",
        "Noto Serif Display",
        "Pinyon Script",
        "Playfair Display",
        "Prata",
        "Unbounded",
    }
)

#: Hiệu ứng nền của web thiệp (`canvas` của thư viện render). `none` = tắt.
THEME_AMBIENTS: Final[frozenset[str]] = frozenset(
    {
        "none",
        "petals",
        "lanterns",
        "bokeh",
        "meteor",
        "fireworks",
        "sparkle",
        "dust",
        "confetti",
        "magnet",
    }
)
THEME_DENSITY_RANGE: Final[tuple[float, float]] = (0.2, 2.0)

#: Các phần của web thiệp sắp xếp / ẩn được. Khoá trùng `SECTION_KEYS` phía web.
SITE_SECTIONS: Final[tuple[str, ...]] = (
    "couple",
    "events",
    "countdown",
    "gallery",
    "gift",  # phong bì mừng cưới ngay sau album
    "rsvp",
    "wishes",
)

__all__ = [
    "CHECKLIST_IDS",
    "GUEST_GROUPS",
    "MAX_EVENTS",
    "SITE_SECTIONS",
    "THEME_AMBIENTS",
    "THEME_DENSITY_RANGE",
    "THEME_FONTS",
    "WORDING_KEYS",
    "EventKind",
    "OpenStyle",
    "Side",
    "Tone",
]
