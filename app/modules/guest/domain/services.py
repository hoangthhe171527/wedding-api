"""Hàm thuần của `guest`: sinh mã khách, kiểm thiệp, đọc danh sách nhập nhanh."""

from __future__ import annotations

import re
import secrets
import unicodedata
from typing import Final

from app.modules.guest.domain.entities import GuestDraft
from app.modules.guest.domain.enums import (
    DEFAULT_GROUP,
    GUEST_GROUPS,
    MAX_PARTY_SIZE,
    Side,
)

_CODE_ALPHABET: Final[str] = "abcdefghijklmnopqrstuvwxyz0123456789"
CODE_LENGTH: Final[int] = 6
_CODE_RE: Final = re.compile(r"^[a-z0-9]{6}$")
#: Tách theo `|` hoặc Tab rồi MỚI bỏ khoảng trắng từng cột. Regex của thiết kế
#: (`\s*[|\t]\s*`) để `\s*` nuốt luôn Tab kế bên, nên dòng dán từ Excel có một
#: ô trống ("Chị<Tab>Mai Anh<Tab><Tab>Đồng nghiệp") bị gộp mất cột và mọi cột
#: sau lệch chỗ — nhóm "Đồng nghiệp" rơi vào ô "Kèm theo".
_SPLIT_RE: Final = re.compile(r"[|\t]")
_BRIDE_SIDE_RE: Final = re.compile(r"g[aá]i", re.IGNORECASE)

FieldErrors = dict[str, list[str]]


def generate_code() -> str:
    """Mã khách 6 ký tự `a-z0-9` — cùng dạng `uid()` của thiết kế.

    36^6 ≈ 2,2 tỉ tổ hợp: đoán mò một mã có thật trong vài trăm khách của một
    xưởng là vô vọng, mà mã vẫn đủ ngắn để đọc qua điện thoại.
    """
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(CODE_LENGTH))


def is_valid_code(code: str) -> bool:
    return bool(_CODE_RE.match(code))


def validate_draft(draft: GuestDraft, *, known_templates: frozenset[str]) -> FieldErrors:
    """Kiểm một thiệp mời. Rỗng là hợp lệ."""
    errors: FieldErrors = {}
    if not draft.name.strip():
        errors["name"] = ["Nhập tên khách trước khi lưu."]
    if draft.group not in GUEST_GROUPS:
        errors["group"] = ["Nhóm khách không tồn tại."]
    if not 1 <= draft.count <= MAX_PARTY_SIZE:
        errors["count"] = [f"Số người từ 1 đến {MAX_PARTY_SIZE}."]
    if draft.template and draft.template not in known_templates:
        errors["template"] = ["Mẫu thiệp không tồn tại."]
    return errors


#: Đuôi link đối tượng: 2-40 ký tự `a-z0-9-`, không mở/đóng bằng gạch.
LINK_SLUG_MAX: Final[int] = 40
_LINK_SLUG_RE: Final = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])$")
LINK_NAME_MAX: Final[int] = 80


def _ascii(text: str) -> str:
    """Bỏ dấu tiếng Việt (kể cả đ/Đ — NFD không tách được hai chữ này)."""
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(
        char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn"
    )


def link_slug_from(name: str) -> str:
    """Đuôi link gợi ý từ tên: "Đồng nghiệp công ty" -> `dong-nghiep-cong-ty`."""
    value = re.sub(r"[^a-z0-9]+", "-", _ascii(name).lower()).strip("-")
    return value[:LINK_SLUG_MAX].strip("-")


def is_valid_link_slug(slug: str) -> bool:
    return bool(_LINK_SLUG_RE.match(slug))


def validate_link(
    *, name: str, slug: str, template: str, known_templates: frozenset[str]
) -> FieldErrors:
    """Kiểm một link đối tượng. Rỗng là hợp lệ."""
    errors: FieldErrors = {}
    if not name.strip():
        errors["name"] = ["Đặt tên để nhận ra link này gửi cho ai."]
    elif len(name.strip()) > LINK_NAME_MAX:
        errors["name"] = [f"Tên tối đa {LINK_NAME_MAX} ký tự."]
    if not is_valid_link_slug(slug):
        errors["slug"] = [
            f"Đuôi link 2-{LINK_SLUG_MAX} ký tự: chữ thường không dấu, số và gạch ngang."
        ]
    if template and template not in known_templates:
        errors["template"] = ["Mẫu thiệp không tồn tại."]
    return errors


def parse_import(text: str) -> tuple[list[GuestDraft], int]:
    """Đọc ô "Nhập nhanh" — y hệt `importGuests()` của thiết kế.

    Mỗi dòng một thiệp, cột cách bằng `|` hoặc Tab (dán từ Excel):
    `Danh xưng | Tên | Kèm theo | Nhóm | Nhà (trai/gái) | Số người`.

    Returns:
        (các thiệp đọc được, số dòng bỏ qua vì thiếu tên).
    """
    drafts: list[GuestDraft] = []
    skipped = 0
    groups_by_lower = {group.lower(): group for group in GUEST_GROUPS}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cols = _SPLIT_RE.split(line)
        if len(cols) < 2 or not cols[1].strip():
            skipped += 1
            continue

        def col(index: int, cols: list[str] = cols) -> str:
            return cols[index].strip() if index < len(cols) else ""

        try:
            count = int(col(5))
        except ValueError:
            count = 1
        drafts.append(
            GuestDraft(
                title=col(0),
                name=col(1),
                plus=col(2),
                group=groups_by_lower.get(col(3).lower(), DEFAULT_GROUP),
                side=Side.GAI if _BRIDE_SIDE_RE.search(col(4)) else Side.TRAI,
                count=min(max(count, 1), MAX_PARTY_SIZE),
            )
        )
    return drafts, skipped


__all__ = [
    "CODE_LENGTH",
    "LINK_NAME_MAX",
    "LINK_SLUG_MAX",
    "FieldErrors",
    "generate_code",
    "is_valid_code",
    "is_valid_link_slug",
    "link_slug_from",
    "parse_import",
    "validate_draft",
    "validate_link",
]
