"""Hàm thuần của `invitation`: chọn mẫu cho khách, lọc dữ liệu công khai."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, Final

#: Mẫu lùi cuối cùng — mẫu duy nhất "Đại Lễ Hỷ Sự" (bản chép `DEFAULT_TEMPLATE_KEY`
#: của `template`, §1.2).
FALLBACK_TEMPLATE: Final[str] = "daile"
#: Link đối tượng chọn "không video" (bản chép `LINK_NO_INTRO` của `guest`, §1.2).
NO_INTRO: Final[str] = "none"

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
        "photo_frame",
        "slug",
        "site_url",
    }
)


#: Trường giao diện lấy từ design của mẫu đang hiện (bản chép `TemplateDesign` của `wedding`).
LOOK_KEYS: Final[tuple[str, ...]] = (
    "theme",
    "card_design",
    "intro",
    "open_style",
    "music_url",
    "photo_frame",
)
_EMPTY_LOOK: Final[dict[str, Any]] = {
    "theme": {},
    "card_design": {"enabled": False, "base": "", "layers": []},
    "intro": "",
    "open_style": "",
    "music_url": "",
    "photo_frame": "none",
}


def effective_template(
    *,
    guest_link: dict[str, Any] | None,
    url_link: dict[str, Any] | None,
    default_template: str,
) -> str:
    """Mẫu của link khách thuộc về -> mẫu của link trên URL -> mẫu chính -> mẫu lùi.

    Link riêng của khách thắng link trên URL: link riêng nhắm đúng một người.
    """
    for link in (guest_link, url_link):
        if link and link.get("template"):
            return str(link["template"])
    return default_template or FALLBACK_TEMPLATE


def _same(key: str) -> str:
    return key


def apply_design(
    snapshot: dict[str, Any],
    template: str,
    canonical: Callable[[str], str] = _same,
) -> dict[str, Any]:
    """Đè phần nhìn của `snapshot` bằng design của `template`.

    Mẫu chưa được design: dùng mặc định của mẫu (giao diện rỗng) — KHÔNG lấy màu
    của mẫu chính, vì màu đó chọn cho bố cục khác. Riêng mẫu chính chưa có design
    (dữ liệu trước khi chuyển đổi) thì giữ nguyên trường cũ.

    `canonical` đổi khoá mẫu đã nghỉ sang khoá thay thế (do bên gọi truyền vào, domain
    không import module khác): design và mẫu chính được so theo khoá chuẩn.
    """
    wanted = canonical(template)
    designs = snapshot.get("designs") or {}
    look = designs.get(template)
    if look is None:
        look = designs.get(wanted)
    if look is None:
        look = next((item for key, item in designs.items() if canonical(key) == wanted), None)
    if look is None:
        main = canonical(str(snapshot.get("default_template") or FALLBACK_TEMPLATE))
        if wanted == main:
            return snapshot
        look = _EMPTY_LOOK
    return {
        **snapshot,
        **{key: copy.deepcopy(look.get(key, _EMPTY_LOOK[key])) for key in LOOK_KEYS},
    }


def effective_intro(wedding_intro: str) -> str:
    """Id video mở thiệp của design đang hiện; `none` hay rỗng = không video."""
    chosen = wedding_intro.strip()
    return "" if chosen == NO_INTRO else chosen


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
    "LOOK_KEYS",
    "NO_INTRO",
    "PUBLIC_WEDDING_KEYS",
    "apply_design",
    "effective_intro",
    "effective_template",
    "for_audience",
    "public_guest",
    "public_wedding",
]
