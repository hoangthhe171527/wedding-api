"""Đồng bộ design riêng theo mẫu với các trường giao diện cũ (spec §5.1).

Luật duy nhất: trường cũ (`theme`, `card_design`, `intro`, `open_style`,
`music_url`) LUÔN bằng `designs[mẫu chính]` sau khi lưu.

* Client mới gửi `designs` -> designs thắng, trường cũ chép theo mẫu chính
  (thiếu design mẫu chính thì lấy từ trường cũ client gửi).
* Client cũ (app Flutter) không gửi `designs` -> giữ designs đã lưu, chỉ thay
  design mẫu chính bằng trường cũ client gửi.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from app.modules.wedding.domain.entities import TemplateDesign, WeddingContent

#: Mẫu lùi khi đám cưới chưa chọn mẫu chính — bản chép `DEFAULT_TEMPLATE_KEY` của `template` (§1.2).
FALLBACK_TEMPLATE: Final[str] = "daile"
#: Trần số design — đủ cho mọi mẫu của bộ mẫu, chặn payload phình vô hạn.
MAX_DESIGNS: Final[int] = 60


def main_key(content: WeddingContent) -> str:
    return content.default_template or FALLBACK_TEMPLATE


def legacy_design(content: WeddingContent) -> TemplateDesign:
    """Design dựng từ các trường cũ."""
    return TemplateDesign(
        theme=content.theme,
        card_design=content.card_design,
        intro=content.intro,
        open_style=content.open_style,
        music_url=content.music_url,
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


def normalize_designs(
    content: WeddingContent, *, designs_sent: bool, stored: WeddingContent | None
) -> WeddingContent:
    """Nội dung sắp lưu, đã đồng bộ trường cũ <-> designs[mẫu chính]."""
    key = main_key(content)
    if designs_sent:
        designs = dict(content.designs)
        designs.setdefault(key, legacy_design(content))
    else:
        designs = dict(stored.designs) if stored is not None else {}
        designs[key] = legacy_design(content)
    return _mirror(content, designs)


__all__ = [
    "FALLBACK_TEMPLATE",
    "MAX_DESIGNS",
    "legacy_design",
    "main_design",
    "main_key",
    "normalize_designs",
]
