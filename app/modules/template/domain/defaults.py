"""Mặc định hệ thống do đội vận hành đặt — áp cho mọi xưởng.

* `group_templates` / `default_template`: xưởng MỚI nhận mẫu theo nhóm khách này
  lúc khởi tạo (khách đổi lại được).
* `wording` / `messages`: câu chữ mặc định theo giọng văn — dùng khi xưởng chưa tự
  sửa ô đó. Không chép vào xưởng, nên đổi ở đây là mọi thiệp chưa sửa đổi theo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from app.modules.template.domain.enums import GUEST_GROUPS, WORDING_KEYS, Tone

MAX_WORDING: Final[int] = 300
MAX_MESSAGE: Final[int] = 1000


@dataclass(frozen=True, slots=True)
class CatalogDefaults:
    group_templates: dict[str, str] = field(default_factory=dict)
    default_template: str = ""
    wording: dict[str, dict[str, str]] = field(default_factory=dict)
    messages: dict[str, str] = field(default_factory=dict)


def clean_defaults(defaults: CatalogDefaults) -> CatalogDefaults:
    """Bỏ ô trống (ô trống = dùng câu gốc của thiết kế) và khoảng trắng thừa."""
    return CatalogDefaults(
        group_templates={k: v.strip() for k, v in defaults.group_templates.items() if v.strip()},
        default_template=defaults.default_template.strip(),
        wording={
            tone: {k: v.strip() for k, v in fields.items() if v.strip()}
            for tone, fields in defaults.wording.items()
            if any(v.strip() for v in fields.values())
        },
        messages={k: v.strip() for k, v in defaults.messages.items() if v.strip()},
    )


def defaults_errors(
    defaults: CatalogDefaults, *, known_templates: frozenset[str]
) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}

    def add(key: str, message: str) -> None:
        errors.setdefault(key, []).append(message)

    tones = {item.value for item in Tone}
    for group, key in defaults.group_templates.items():
        if group not in GUEST_GROUPS:
            add("group_templates", f"Nhóm khách “{group}” không tồn tại.")
        elif key not in known_templates:
            add(f"group_templates.{group}", "Mẫu không tồn tại.")
    if defaults.default_template and defaults.default_template not in known_templates:
        add("default_template", "Mẫu không tồn tại.")
    for tone, fields in defaults.wording.items():
        if tone not in tones:
            add("wording", f"Giọng văn “{tone}” không tồn tại.")
            continue
        for key, value in fields.items():
            if key not in WORDING_KEYS:
                add(f"wording.{tone}", f"Ô câu chữ “{key}” không tồn tại.")
            elif len(value) > MAX_WORDING:
                add(f"wording.{tone}.{key}", f"Tối đa {MAX_WORDING} ký tự.")
    for tone, value in defaults.messages.items():
        if tone not in tones:
            add("messages", f"Giọng văn “{tone}” không tồn tại.")
        elif len(value) > MAX_MESSAGE:
            add(f"messages.{tone}", f"Tối đa {MAX_MESSAGE} ký tự.")
    return errors


__all__ = ["CatalogDefaults", "clean_defaults", "defaults_errors"]
