"""Hàm thuần của `invitation`: chọn mẫu cho khách, lọc dữ liệu công khai."""

from __future__ import annotations

from typing import Any, Final

#: Mẫu lùi cuối cùng — đúng `effTpl()` của thiết kế.
FALLBACK_TEMPLATE: Final[str] = "ngoctrai"

#: DANH SÁCH CHO PHÉP — chỉ những trường web thiệp thật sự vẽ mới lên trang công khai.
#: Trường mới thêm vào đám cưới mặc định là RIÊNG TƯ cho tới khi được khai ở đây.
#: Cố ý vắng mặt: `messages` (tin nhắn mời soạn sẵn, có thể chứa ghi chú riêng),
#: `group_templates` (lộ cách cặp đôi phân loại khách). Số điện thoại cô dâu chú rể
#: CÓ lên thiệp: mục "liên hệ" dưới phần xác nhận tham dự của thiết kế dùng chúng.
PUBLIC_WEDDING_KEYS: Final[frozenset[str]] = frozenset(
    {
        "groom",
        "bride",
        "groom_parents",
        "bride_parents",
        "events",
        "story",
        "quote",
        "rsvp",
        "gift",
        "music_url",
        "default_template",
        "wording",
        "open_style",
        "theme",
        "card_design",
        "schedule",
        "dress_code",
        "slug",
        "site_url",
    }
)


def effective_template(
    *,
    guest: dict[str, Any] | None,
    group_templates: dict[str, str],
    default_template: str,
) -> str:
    """Mẫu riêng của khách -> mẫu của nhóm -> mẫu mặc định -> mẫu lùi."""
    if guest is not None:
        if guest.get("template"):
            return str(guest["template"])
        by_group = group_templates.get(str(guest.get("group", "")))
        if by_group:
            return by_group
    return default_template or FALLBACK_TEMPLATE


def public_wedding(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Bản công khai của đám cưới.

    Tắt hộp mừng cưới thì số tài khoản bị BỎ khỏi payload, không chỉ bị ẩn ở
    giao diện: dữ liệu đã nằm trong phản hồi là đã công khai.
    """
    data = {key: value for key, value in snapshot.items() if key in PUBLIC_WEDDING_KEYS}
    gift = dict(data.get("gift") or {})
    if not gift.get("show"):
        empty = {"bank": "", "number": "", "holder": ""}
        data["gift"] = {"show": False, "groom": dict(empty), "bride": dict(empty)}
    return data


def public_guest(guest: dict[str, Any] | None) -> dict[str, Any] | None:
    """Khách công khai: bỏ nhóm (chỉ dùng để chọn mẫu)."""
    if guest is None:
        return None
    return {key: value for key, value in guest.items() if key != "group"}


__all__ = [
    "FALLBACK_TEMPLATE",
    "PUBLIC_WEDDING_KEYS",
    "effective_template",
    "public_guest",
    "public_wedding",
]
