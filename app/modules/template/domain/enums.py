"""Enum của `template` — khớp nguyên văn `InviteLib` trong thiết kế."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class Family(StrEnum):
    """Dòng mẫu (bộ lọc chip ở tab Mẫu thiệp)."""

    MINIMAL = "minimal"
    #: Web thiệp kiểu kể chuyện (bộ máy Story ở web: `src/lib/story`).
    STORY_MINIMAL = "story-minimal"
    STORY_TRAD = "story-trad"
    STORY_FLORAL = "story-floral"
    STORY_LUXE = "story-luxe"
    STORY_ROMANCE = "story-romance"
    MOTION = "motion"
    ROYAL = "royal"
    MODERN = "modern"
    RED = "red"
    TRAD = "trad"
    GOLD = "gold"
    PASTEL = "pastel"
    FLORA = "flora"


#: Nhóm khách — bản CHÉP của `guest.domain.enums.GUEST_GROUPS` (§1.2), khoá bởi
#: `tests/modules/test_parity.py`.
GUEST_GROUPS: Final[tuple[str, ...]] = (
    "Họ hàng",
    "Bạn bố mẹ",
    "Hàng xóm",
    "Thầy cô",
    "Đồng nghiệp",
    "Đối tác",
    "Bạn bè",
)

#: Ô câu chữ — bản CHÉP của `wedding.domain.enums.WORDING_KEYS` (§1.2).
WORDING_KEYS: Final[frozenset[str]] = frozenset(
    {"eyebrow", "eyebrowG", "invite", "announce", "attend", "closing", "thanks"}
)


class Tone(StrEnum):
    """Giọng văn — quyết định câu chữ in trên thiệp."""

    FAMILY = "family"
    FORMAL = "formal"
    FRIENDS = "friends"


class Layout(StrEnum):
    """Bố cục thiệp — mỗi bố cục một bộ CSS riêng ở web."""

    LUX = "lux"
    CINEMA = "cinema"
    GLASS = "glass"
    EDITORIAL = "editorial"
    TRAD = "trad"
    DECO = "deco"
    FLORA = "flora"
    LOTUS = "lotus"
    #: Bộ "Tối giản" (web: `lib/invite/modern-templates.ts`).
    MINIMAL = "minimal"
    TYPE = "type"
    STORY = "story"


class Tier(StrEnum):
    """Hạng mẫu — gói tối thiểu cần có để XUẤT BẢN web thiệp dùng mẫu này.

    Trùng slug với `billing.domain.enums.Plan` (bản chép, §1.2): mẫu hạng
    `standard` cần Gói Hỷ trở lên, `premium` cần Gói Lộng Lẫy.
    """

    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"


TIER_LABELS: Final[dict[Tier, str]] = {
    Tier.FREE: "Miễn phí",
    Tier.STANDARD: "Gói Hỷ",
    Tier.PREMIUM: "Gói Lộng Lẫy",
}

FAMILY_LABELS: Final[dict[Family, str]] = {
    Family.MOTION: "Hoạt hình",
    Family.ROYAL: "Cung đình lộng lẫy",
    Family.MODERN: "Hiện đại",
    Family.MINIMAL: "Tối giản",
    Family.STORY_MINIMAL: "Tối giản sang trọng",
    Family.STORY_TRAD: "Hỷ truyền thống",
    Family.STORY_FLORAL: "Hoa mộc",
    Family.STORY_LUXE: "Hoàng gia",
    Family.STORY_ROMANCE: "Lãng mạn",
    Family.RED: "Sắc đỏ",
    Family.TRAD: "Truyền thống Việt",
    Family.GOLD: "Vàng champagne",
    Family.PASTEL: "Pastel ngọt ngào",
    Family.FLORA: "Hoa lá màu nước",
}

TONE_LABELS: Final[dict[Tone, str]] = {
    Tone.FAMILY: "Trang trọng – gia đình",
    Tone.FORMAL: "Lịch sự – công việc",
    Tone.FRIENDS: "Thân mật – bạn bè",
}

__all__ = ["FAMILY_LABELS", "TIER_LABELS", "TONE_LABELS", "Family", "Layout", "Tier", "Tone"]
