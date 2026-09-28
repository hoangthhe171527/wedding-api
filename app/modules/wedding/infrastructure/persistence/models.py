"""Beanie Document của `wedding` — collection `weddings`.

Nội dung đám cưới nhúng thẳng trong một document (đúng hình `W` của thiết kế):
luôn đọc/ghi trọn cùng nhau, và nhỏ (vài KB) — tách collection chỉ thêm join.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from app.core.base_model import (
    ASCENDING,
    DESCENDING,
    Document,
    IndexModel,
    TenantScopedDocument,
)


class PersonModel(BaseModel):
    full: str = ""
    short: str = ""
    rank: str = ""
    phone: str = ""


class ParentsModel(BaseModel):
    father: str = ""
    mother: str = ""
    address: str = ""


class EventModel(BaseModel):
    id: str
    name: str = ""
    kind: str = "tiec"
    side: str = "trai"
    date: str = ""
    time: str = ""
    venue: str = ""
    address: str = ""
    map_url: str = ""
    arrival: str = ""


class ScheduleItemModel(BaseModel):
    time: str = ""
    label: str = ""


class DressCodeModel(BaseModel):
    note: str = ""
    colors: list[str] = Field(default_factory=list)


class RsvpModel(BaseModel):
    url: str = ""
    deadline: str = ""


class BankAccountModel(BaseModel):
    bank: str = ""
    number: str = ""
    holder: str = ""
    qr: str = ""


class GiftModel(BaseModel):
    show: bool = False
    groom: BankAccountModel = Field(default_factory=BankAccountModel)
    bride: BankAccountModel = Field(default_factory=BankAccountModel)


class ThemeModel(BaseModel):
    accent: str = ""
    accent2: str = ""
    ink: str = ""
    font_display: str = ""
    font_script: str = ""
    font_body: str = ""
    ambient: str = ""
    density: float = 0.0
    intro: str = ""
    intro2: str = ""
    sections: list[str] = Field(default_factory=list)
    hidden: list[str] = Field(default_factory=list)


class DesignLayerModel(BaseModel):
    id: str
    kind: str
    x: float = 10.0
    y: float = 10.0
    w: float = 80.0
    h: float = 10.0
    rotate: float = 0.0
    opacity: float = 1.0
    hidden: bool = False
    locked: bool = False
    text: str = ""
    field: str = ""
    font: str = ""
    size: float = 4.0
    color: str = ""
    align: str = "center"
    weight: int = 400
    italic: bool = False
    upper: bool = False
    spacing: float = 0.0
    line: float = 1.2
    foil: bool = False
    photo: int = 0
    fit: str = "cover"
    radius: float = 0.0
    decor: str = ""
    shape: str = "rect"
    fill: str = ""
    stroke: str = ""
    stroke_w: float = 0.0


class CardDesignModel(BaseModel):
    enabled: bool = False
    base: str = ""
    layers: list[DesignLayerModel] = Field(default_factory=list)


class WeddingDocument(TenantScopedDocument):
    """Đám cưới của một xưởng — đúng một document mỗi xưởng."""

    slug: str
    published: bool = False
    groom: PersonModel = Field(default_factory=PersonModel)
    bride: PersonModel = Field(default_factory=PersonModel)
    groom_parents: ParentsModel = Field(default_factory=ParentsModel)
    bride_parents: ParentsModel = Field(default_factory=ParentsModel)
    events: list[EventModel] = Field(default_factory=list)
    story: str = ""
    quote: str = ""
    rsvp: RsvpModel = Field(default_factory=RsvpModel)
    gift: GiftModel = Field(default_factory=GiftModel)
    music_url: str = ""
    default_template: str = ""
    group_templates: dict[str, str] = Field(default_factory=dict)
    wording: dict[str, dict[str, str]] = Field(default_factory=dict)
    messages: dict[str, str] = Field(default_factory=dict)
    open_style: str = ""
    theme: ThemeModel = Field(default_factory=ThemeModel)
    card_design: CardDesignModel = Field(default_factory=CardDesignModel)
    schedule: list[ScheduleItemModel] = Field(default_factory=list)
    dress_code: DressCodeModel = Field(default_factory=DressCodeModel)
    checklist: dict[str, bool] = Field(default_factory=dict)

    class Settings(TenantScopedDocument.Settings):
        name = "weddings"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            IndexModel(
                [("tenant_id", ASCENDING)],
                name="uq_weddings_tenant",
                unique=True,
                partialFilterExpression={"deleted_at": None},
            ),
            # Ngoại lệ có chủ ý với §0.4: link công khai `/invite/<slug>` được
            # tra khi chưa biết tenant — slug là khoá duy nhất toàn hệ thống.
            IndexModel([("slug", ASCENDING)], name="uq_weddings_slug", unique=True),
            # Màn giám sát xưởng: mới cập nhật trước.
            IndexModel(
                [("deleted_at", ASCENDING), ("updated_at", DESCENDING)], name="ix_weddings_recent"
            ),
        ]


DOCUMENTS: list[type[Document]] = [WeddingDocument]

__all__ = [
    "DOCUMENTS",
    "BankAccountModel",
    "EventModel",
    "GiftModel",
    "ParentsModel",
    "PersonModel",
    "RsvpModel",
    "ThemeModel",
    "WeddingDocument",
]
