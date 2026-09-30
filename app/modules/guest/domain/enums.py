"""Enum và hằng của `guest` — khớp nguyên văn thiết kế."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class Side(StrEnum):
    """Khách của nhà trai hay nhà gái — quyết định tiêu đề thiệp và thứ tự tên."""

    TRAI = "trai"
    GAI = "gai"


class RsvpStatus(StrEnum):
    """Phản hồi của khách. `none` = chưa phản hồi (thiết kế dùng chuỗi rỗng)."""

    NONE = "none"
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"


RSVP_LABELS: Final[dict[RsvpStatus, str]] = {
    RsvpStatus.NONE: "Chưa phản hồi",
    RsvpStatus.YES: "Sẽ đến",
    RsvpStatus.MAYBE: "Chưa chắc",
    RsvpStatus.NO: "Không đến",
}

#: Nhóm khách — bản GỐC. `wedding.domain.enums.GUEST_GROUPS` là bản chép (§1.2).
GUEST_GROUPS: Final[tuple[str, ...]] = (
    "Họ hàng",
    "Bạn bố mẹ",
    "Hàng xóm",
    "Thầy cô",
    "Đồng nghiệp",
    "Đối tác",
    "Bạn bè",
)

#: Nhóm gán khi dòng nhập nhanh không ghi nhóm hoặc ghi nhóm lạ.
DEFAULT_GROUP: Final[str] = "Bạn bè"

MAX_GUESTS_PER_STUDIO: Final[int] = 2000
#: Số người tối đa một phản hồi tự khai (khác `MAX_PARTY_SIZE` người soạn đặt).
MAX_REPLY_PARTY: Final[int] = 20
MAX_WISH_LENGTH: Final[int] = 500
MAX_PARTY_SIZE: Final[int] = 50
#: Link theo đối tượng mỗi xưởng — đủ cho mọi nhóm người một đám cưới có.
MAX_LINKS_PER_STUDIO: Final[int] = 30

__all__ = [
    "DEFAULT_GROUP",
    "GUEST_GROUPS",
    "MAX_GUESTS_PER_STUDIO",
    "MAX_LINKS_PER_STUDIO",
    "MAX_PARTY_SIZE",
    "MAX_REPLY_PARTY",
    "MAX_WISH_LENGTH",
    "RSVP_LABELS",
    "RsvpStatus",
    "Side",
]
