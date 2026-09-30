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
    link: dict[str, Any] | None = None,
) -> str:
    """Mẫu riêng của khách -> mẫu của nhóm -> mẫu của link đối tượng -> mẫu mặc định
    -> mẫu lùi.

    Khách có link riêng mở qua link đối tượng (hiếm: `/<đuôi>#<mã>`) vẫn thấy mẫu
    dành riêng cho mình — link riêng nhắm đúng một người nên được ưu tiên.
    """
    if guest is not None:
        if guest.get("template"):
            return str(guest["template"])
        by_group = group_templates.get(str(guest.get("group", "")))
        if by_group:
            return by_group
    if link is not None and link.get("template"):
        return str(link["template"])
    return default_template or FALLBACK_TEMPLATE


def public_wedding(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Bản công khai của đám cưới.

    Tắt hộp mừng cưới thì số tài khoản bị BỎ khỏi payload, không chỉ bị ẩn ở
    giao diện: dữ liệu đã nằm trong phản hồi là đã công khai.
    """
    data = {key: value for key, value in snapshot.items() if key in PUBLIC_WEDDING_KEYS}
    gift = dict(data.get("gift") or {})
    if not gift.get("show"):
        empty = {"bank": "", "number": "", "holder": "", "qr": ""}
        data["gift"] = {"show": False, "groom": dict(empty), "bride": dict(empty)}
    return data


def for_audience(wedding: dict[str, Any], link: dict[str, Any] | None) -> dict[str, Any]:
    """Bản công khai cho người mở link đối tượng: chỉ những lễ tiệc nhóm đó được mời.

    Lọc ở máy chủ chứ không chỉ ẩn ở giao diện — đồng nghiệp mở link không nhận
    được giờ, địa chỉ tiệc nhà bên kia. Link chọn lễ tiệc không còn (đã xoá) thì
    giữ nguyên danh sách: thiệp không bao giờ rỗng lễ tiệc.
    """
    wanted = set((link or {}).get("events") or ())
    if not wanted:
        return wedding
    events = [item for item in wedding.get("events") or [] if item.get("id") in wanted]
    return {**wedding, "events": events} if events else wedding


def public_guest(guest: dict[str, Any] | None) -> dict[str, Any] | None:
    """Khách công khai: bỏ nhóm (chỉ dùng để chọn mẫu)."""
    if guest is None:
        return None
    return {key: value for key, value in guest.items() if key != "group"}


__all__ = [
    "FALLBACK_TEMPLATE",
    "PUBLIC_WEDDING_KEYS",
    "effective_template",
    "for_audience",
    "public_guest",
    "public_wedding",
]
