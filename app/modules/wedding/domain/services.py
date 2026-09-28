"""Hàm thuần của `wedding`: kiểm nội dung, sinh slug công khai."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Final

from app.modules.wedding.domain.design import validate_design
from app.modules.wedding.domain.entities import WeddingContent
from app.modules.wedding.domain.enums import (
    CHECKLIST_IDS,
    GUEST_GROUPS,
    MAX_EVENTS,
    SITE_SECTIONS,
    THEME_AMBIENTS,
    THEME_DENSITY_RANGE,
    THEME_FONTS,
    WORDING_KEYS,
    Tone,
)

#: Lịch trình ngày cưới và màu dress code: đủ cho một ngày cưới, không thành danh sách dài.
MAX_SCHEDULE: Final = 12
MAX_DRESS_COLORS: Final = 6
_TIME_RE: Final = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_SLUG_RE: Final = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,58}[a-z0-9])$")
_URL_RE: Final = re.compile(r"^https?://\S+$", re.IGNORECASE)
_HEX_RE: Final = re.compile(r"^#[0-9a-fA-F]{6}$")
#: Chỉ ảnh raster dạng base64 — không nhận SVG hay URL ngoài (ảnh hiện thẳng trên web thiệp).
_QR_RE: Final = re.compile(r"^data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/]+=*$")

#: Slug không được trùng đường dẫn hệ thống của web.
RESERVED_SLUGS: Final[frozenset[str]] = frozenset(
    {"admin", "api", "auth", "invite", "login", "register", "static", "assets", "thiep"}
)

FieldErrors = dict[str, list[str]]


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_content(content: WeddingContent, *, known_templates: frozenset[str]) -> FieldErrors:
    """Kiểm nội dung đám cưới. Trả lỗi theo đường dẫn trường; rỗng là hợp lệ.

    Chỉ chặn thứ làm web thiệp HỎNG (ngày sai, link lạ, mẫu không tồn tại). Trường
    để trống là hợp lệ: form lưu tự động từng phím gõ, nửa chừng luôn có ô trống.
    """
    errors: FieldErrors = {}

    def add(path: str, message: str) -> None:
        errors.setdefault(path, []).append(message)

    if len(content.events) > MAX_EVENTS:
        add("events", f"Tối đa {MAX_EVENTS} sự kiện.")
    seen_ids: set[str] = set()
    for index, event in enumerate(content.events):
        base = f"events.{index}"
        if event.id in seen_ids:
            add(f"{base}.id", "Mã sự kiện bị trùng.")
        seen_ids.add(event.id)
        if event.date and not _is_iso_date(event.date):
            add(f"{base}.date", "Ngày không đúng định dạng yyyy-mm-dd.")
        if event.time and not _TIME_RE.match(event.time):
            add(f"{base}.time", "Giờ không đúng định dạng HH:MM.")
        if event.map_url and not _URL_RE.match(event.map_url):
            add(f"{base}.map_url", "Link bản đồ phải bắt đầu bằng http:// hoặc https://.")
        if event.arrival and not _TIME_RE.match(event.arrival):
            add(f"{base}.arrival", "Giờ đón khách không đúng định dạng HH:MM.")

    if len(content.schedule) > MAX_SCHEDULE:
        add("schedule", f"Lịch trình tối đa {MAX_SCHEDULE} mốc.")
    for index, item in enumerate(content.schedule):
        if item.time and not _TIME_RE.match(item.time):
            add(f"schedule.{index}.time", "Giờ không đúng định dạng HH:MM.")
    if len(content.dress_code.colors) > MAX_DRESS_COLORS:
        add("dress_code.colors", f"Tối đa {MAX_DRESS_COLORS} màu.")
    for index, color in enumerate(content.dress_code.colors):
        if not _HEX_RE.match(color):
            add(f"dress_code.colors.{index}", "Màu phải có dạng #RRGGBB.")

    for side, account in (("groom", content.gift.groom), ("bride", content.gift.bride)):
        if account.qr and not _QR_RE.match(account.qr):
            add(f"gift.{side}.qr", "Ảnh QR phải là PNG, JPEG hoặc WebP.")

    if content.rsvp.url and not _URL_RE.match(content.rsvp.url):
        add("rsvp.url", "Link xác nhận phải bắt đầu bằng http:// hoặc https://.")
    if content.rsvp.deadline and not _is_iso_date(content.rsvp.deadline):
        add("rsvp.deadline", "Ngày không đúng định dạng yyyy-mm-dd.")
    if content.music_url and not _URL_RE.match(content.music_url):
        add("music_url", "Link nhạc nền phải bắt đầu bằng http:// hoặc https://.")

    if content.default_template and content.default_template not in known_templates:
        add("default_template", "Mẫu thiệp không tồn tại.")
    for group, key in content.group_templates.items():
        if group not in GUEST_GROUPS:
            add("group_templates", f"Nhóm khách “{group}” không tồn tại.")
        elif key not in known_templates:
            add(f"group_templates.{group}", "Mẫu thiệp không tồn tại.")

    tones = {tone.value for tone in Tone}
    for tone, fields in content.wording.items():
        if tone not in tones:
            add("wording", f"Giọng văn “{tone}” không tồn tại.")
            continue
        for key in fields:
            if key not in WORDING_KEYS:
                add(f"wording.{tone}", f"Ô câu chữ “{key}” không tồn tại.")
    for tone in content.messages:
        if tone not in tones:
            add("messages", f"Giọng văn “{tone}” không tồn tại.")

    theme = content.theme
    for name in ("accent", "accent2", "ink", "intro", "intro2"):
        value = getattr(theme, name)
        if value and not _HEX_RE.match(value):
            add(f"theme.{name}", "Màu phải có dạng #RRGGBB.")
    for name in ("font_display", "font_script", "font_body"):
        value = getattr(theme, name)
        if value and value not in THEME_FONTS:
            add(f"theme.{name}", "Font không có trong danh sách.")
    if theme.ambient and theme.ambient not in THEME_AMBIENTS:
        add("theme.ambient", "Hiệu ứng nền không tồn tại.")
    low, high = THEME_DENSITY_RANGE
    if theme.density and not low <= theme.density <= high:
        add("theme.density", f"Mật độ từ {low} đến {high}.")
    for name in ("sections", "hidden"):
        keys = getattr(theme, name)
        if any(key not in SITE_SECTIONS for key in keys) or len(set(keys)) != len(keys):
            add(f"theme.{name}", "Danh sách phần của web thiệp không hợp lệ.")
    for path, messages in validate_design(
        content.card_design, known_templates=known_templates
    ).items():
        for message in messages:
            add(path, message)
    return errors


def plan_usage(
    content: WeddingContent, *, guest_count: int, guest_templates: set[str], groups: set[str]
) -> dict[str, object]:
    """Những gì đám cưới này đang dùng, dạng dữ liệu thuần gửi sang `billing`.

    Mẫu đang dùng = mẫu mặc định (link chung) + mẫu của những NHÓM đang có khách
    + mẫu gán riêng cho từng khách. Mẫu của nhóm không có khách nào không tính:
    không ai nhìn thấy nó.
    """
    templates = set(guest_templates)
    if content.default_template:
        templates.add(content.default_template)
    templates.update(
        key for group, key in content.group_templates.items() if group in groups and key
    )
    return {
        "templates": sorted(templates),
        "open_style": content.open_style.value,
        "guest_count": guest_count,
        "music": bool(content.music_url),
        "gift": content.gift.show,
        "theme": content.theme.customized,
        "design": content.card_design.enabled,
    }


def clean_checklist(done: dict[str, bool]) -> dict[str, bool]:
    """Chỉ giữ id có trong lộ trình và đang được đánh dấu."""
    return {key: True for key, value in done.items() if key in CHECKLIST_IDS and value}


def _ascii(text: str) -> str:
    """Bỏ dấu tiếng Việt (kể cả đ/Đ — NFD không tách được hai chữ này)."""
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(
        char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn"
    )


def slugify(text: str) -> str:
    """Chuỗi bất kỳ -> slug `a-z0-9-`, giống hàm `slug()` của thiết kế."""
    value = re.sub(r"[^a-z0-9]+", "-", _ascii(text).lower()).strip("-")
    return value[:60].strip("-")


def couple_slug(groom_short: str, bride_short: str) -> str:
    """Slug gợi ý theo `coupleSlug()` của thiết kế: `h-hoang-ha` cho Huy Hoàng & Hải Hà."""
    groom_words = groom_short.split() or ["chu", "re"]
    bride_words = bride_short.split() or ["co", "dau"]
    initial = _ascii(groom_words[-1])[:1]
    return slugify(f"{initial}-{groom_words[-1]}-{bride_words[-1]}") or "thiep-cuoi"


def slug_problem(slug: str) -> str | None:
    """Lý do slug không dùng được, hoặc None nếu hợp lệ."""
    if not _SLUG_RE.match(slug):
        return "Đường dẫn chỉ gồm chữ thường không dấu, số và dấu gạch ngang (3–60 ký tự)."
    if "--" in slug:
        return "Đường dẫn không được có hai dấu gạch ngang liền nhau."
    if slug in RESERVED_SLUGS:
        return "Đường dẫn này trùng tên hệ thống. Hãy chọn tên khác."
    return None


__all__ = [
    "RESERVED_SLUGS",
    "FieldErrors",
    "clean_checklist",
    "couple_slug",
    "plan_usage",
    "slug_problem",
    "slugify",
    "validate_content",
]
