"""Đồng bộ design riêng theo mẫu với các trường giao diện cũ (spec §5.1).

Luật duy nhất: trường cũ (`theme`, `card_design`, `intro`, `open_style`,
`music_url`) LUÔN bằng `designs[mẫu chính]` sau khi lưu.

* Client mới gửi `designs` -> designs thắng, trường cũ chép theo mẫu chính
  (thiếu design mẫu chính thì lấy từ trường cũ client gửi).
* Ngoại lệ: app Flutter gửi lại nguyên `designs` của lần GET trước và chỉ sửa trường
  cũ. `designs[mẫu chính]` y hệt bản đã lưu mà trường cũ đổi -> trường cũ thắng.
* Client cũ (app Flutter) không gửi `designs` -> giữ designs đã lưu, chỉ thay
  design mẫu chính bằng trường cũ client gửi.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Final

from app.modules.wedding.domain.entities import TemplateDesign, WeddingContent

#: Mẫu lùi khi đám cưới chưa chọn mẫu chính — bản chép `DEFAULT_TEMPLATE_KEY` của `template` (§1.2).
FALLBACK_TEMPLATE: Final[str] = "daile"
#: Trần số design — đủ cho mọi mẫu của bộ mẫu, chặn payload phình vô hạn.
MAX_DESIGNS: Final[int] = 60


def main_key(content: WeddingContent) -> str:
    return content.default_template or FALLBACK_TEMPLATE


def legacy_design(content: WeddingContent, kept: TemplateDesign | None = None) -> TemplateDesign:
    """Design dựng từ các trường cũ.

    `kept`: design đang có của mẫu đó — giữ phần chỉ design mới có (`photo_frame`),
    để client cũ ghi trường cũ không xoá mất khung ảnh.
    """
    return TemplateDesign(
        theme=content.theme,
        card_design=content.card_design,
        intro=content.intro,
        open_style=content.open_style,
        music_url=content.music_url,
        photo_frame=kept.photo_frame if kept is not None else "none",
    )


def main_design(content: WeddingContent) -> TemplateDesign:
    return content.designs.get(main_key(content)) or legacy_design(content)


def _mirror(content: WeddingContent, designs: dict[str, TemplateDesign]) -> WeddingContent:
    main = designs[main_key(content)]
    return replace(
        content,
        designs=designs,
        theme=main.theme,
        card_design=main.card_design,
        intro=main.intro,
        open_style=main.open_style,
        music_url=main.music_url,
    )


def canonical_keys(content: WeddingContent, canonical: Callable[[str], str]) -> WeddingContent:
    """Mẫu chính và khoá design theo khoá chuẩn (mẫu đã nghỉ -> mẫu thay thế).

    `canonical` do bên gọi truyền vào (domain không import module khác). Design gửi
    dưới khoá đã nghỉ chỉ dùng khi chưa có design dưới khoá chuẩn.
    """
    designs = {key: item for key, item in content.designs.items() if canonical(key) == key}
    for key, item in content.designs.items():
        designs.setdefault(canonical(key), item)
    return replace(content, default_template=canonical(content.default_template), designs=designs)


def normalize_designs(
    content: WeddingContent, *, designs_sent: bool, stored: WeddingContent | None
) -> WeddingContent:
    """Nội dung sắp lưu, đã đồng bộ trường cũ <-> designs[mẫu chính]."""
    key = main_key(content)
    if designs_sent:
        designs = dict(content.designs)
        legacy = legacy_design(content)
        if (
            stored is not None
            and content.designs.get(key) == stored.designs.get(key)
            and legacy != legacy_design(stored)
        ):
            designs[key] = legacy_design(content, content.designs.get(key))
        else:
            designs.setdefault(key, legacy)
    else:
        designs = dict(stored.designs) if stored is not None else {}
        designs[key] = legacy_design(content, designs.get(key))
    return _mirror(content, designs)


__all__ = [
    "FALLBACK_TEMPLATE",
    "MAX_DESIGNS",
    "canonical_keys",
    "legacy_design",
    "main_design",
    "main_key",
    "normalize_designs",
]
