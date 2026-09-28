"""Schema HTTP của `template`.

`family`/`tone` trả kèm nhãn tiếng Việt dạng `{slug, label}` (§0.3): client không
hardcode bộ nhãn.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.template.domain.defaults import CatalogDefaults
from app.modules.template.domain.entities import Template
from app.modules.template.domain.enums import FAMILY_LABELS, TIER_LABELS, TONE_LABELS, Tier


class LabelOut(BaseModel):
    slug: str
    label: str


class TemplateOut(BaseModel):
    """Một mẫu thiệp. `id` trùng khoá của thư viện render ở web."""

    id: str
    name: str
    family: LabelOut
    tone: LabelOut
    layout: str
    tier: LabelOut
    is_new: bool
    is_active: bool
    sort_order: int

    @classmethod
    def of(cls, item: Template) -> TemplateOut:
        return cls(
            id=item.key,
            name=item.name,
            family=LabelOut(slug=item.family.value, label=FAMILY_LABELS[item.family]),
            tone=LabelOut(slug=item.tone.value, label=TONE_LABELS[item.tone]),
            layout=item.layout.value,
            tier=LabelOut(slug=item.tier.value, label=TIER_LABELS[item.tier]),
            is_new=item.is_new,
            is_active=item.is_active,
            sort_order=item.sort_order,
        )


class TemplatePatchIn(BaseModel):
    """Chỉ gửi trường cần đổi."""

    is_active: bool | None = None
    is_new: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    tier: Tier | None = None


__all__ = ["LabelOut", "TemplateOut", "TemplatePatchIn"]


class CatalogDefaultsIO(BaseModel):
    """Mặc định hệ thống. Ô trống = dùng câu / mẫu gốc của thiết kế."""

    group_templates: dict[str, str] = Field(default_factory=dict)
    default_template: str = Field(default="", max_length=40)
    wording: dict[str, dict[str, str]] = Field(default_factory=dict)
    messages: dict[str, str] = Field(default_factory=dict)

    def to_domain(self) -> CatalogDefaults:
        return CatalogDefaults(
            group_templates=dict(self.group_templates),
            default_template=self.default_template,
            wording={tone: dict(fields) for tone, fields in self.wording.items()},
            messages=dict(self.messages),
        )

    @classmethod
    def of(cls, item: CatalogDefaults) -> CatalogDefaultsIO:
        return cls(
            group_templates=dict(item.group_templates),
            default_template=item.default_template,
            wording={tone: dict(fields) for tone, fields in item.wording.items()},
            messages=dict(item.messages),
        )
